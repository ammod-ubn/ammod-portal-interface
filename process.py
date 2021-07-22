import argparse
import os
import glob
import tempfile
from typing import List
import zipfile
import contextlib
from api_client import ApiClient
from utils import checksum, step_name_to_docker_name, setup_logging
from config import api_base_url, api_config_path

def step(step_name: str, client: ApiClient, source_ids: List[str]):
    """
    Execute a single processing step and upload its results
    """

    step_dir = os.path.join(os.path.dirname(__file__), "steps", step_name)
    assert os.path.isdir(step_dir)
    run_script_filepath = os.path.join(step_dir, "run")

    # run script must be executable
    assert os.access(run_script_filepath, os.X_OK)
    
    # work inside a temporary directory
    with tempfile.TemporaryDirectory() as tmp_dir:
        in_dir = os.path.join(tmp_dir, "in")
        out_dir = os.path.join(tmp_dir, "out")
        os.makedirs(in_dir)
        os.makedirs(out_dir)
        
        # get the metadata of the input record ids
        metadata = client.search_metadata({"white_list": ",".join(source_ids)})
        if metadata["count"] != len(source_ids):
            raise RuntimeError(f"unexpected number of metadata results for ids: {source_ids}")

        # compute the list of source files referenced for metadata upload
        source_files = set()
        for e in metadata["data"]:
            for f in e["files"]:
                source_files.add(f["fileName"])
        source_files = sorted(list(source_files))

        # download and unzip the input metadata
        zip_path = os.path.join(in_dir, "raw.zip")
        client.download_metadata({"white_list": ",".join(source_ids)}, zip_path)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(in_dir)
        os.unlink(zip_path)

        # run the step's run script inside the corresponding docker container
        if os.system(f'''
            docker run --rm --gpus all \
                -m 16g \
                --shm-size=16g \
                -v "{in_dir}:/tmp/in" \
                -v "{out_dir}:/tmp/out" \
                -v "{os.path.abspath(run_script_filepath)}:/tmp/run" \
                {step_name_to_docker_name(step_name)} \
                /tmp/run
        ''') != 0:
            raise RuntimeError(f"error while executing run script for step: {step_name}")

        # gather resulting files
        result_filepaths = sorted([p for p in glob.glob(os.path.join(out_dir, "**", "*"), recursive=True) if os.path.isfile(p)])
        if len(result_filepaths) < 1:
            raise RuntimeError(f"at least one result file is expected, got {len(result_filepaths)}")

        # which metadata keys to copy from the source records
        keys_to_copy = ["deviceID", "serialNumber", "timestamp", "location"]
        metadata = {
            **{key: metadata["data"][0][key] for key in keys_to_copy},
            "files": [
                {
                    "fileName": os.path.basename(result_filepath),
                    "fileSize": os.path.getsize(result_filepath) * 1e-6,  # in megabytes (MB)
                    "md5Checksum": checksum(result_filepath).hexdigest(),
                }
                for result_filepath in result_filepaths
            ],
            "sourceFiles": source_files,
        }

        # upload results
        with contextlib.ExitStack() as stack:
            files = [stack.enter_context(open(result_filepath, "rb")) for result_filepath in result_filepaths]
            client.upload_metadata(metadata, files)


def main():
    setup_logging()
    argparser = argparse.ArgumentParser(description="Executes a processing step and uploads the results")
    argparser.add_argument("step_name", type=str, help="the name of the step to run")
    argparser.add_argument("source_ids", nargs="+", type=str, help="the IDs of the records which should be processed")
    args = argparser.parse_args()
    step(args.step_name, ApiClient(api_base_url, api_config_path), args.source_ids)


if __name__ == "__main__":
    main()