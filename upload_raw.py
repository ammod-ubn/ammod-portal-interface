import argparse
import os
from tqdm.auto import tqdm

from utils import make_api_filename, parse_raw_timestamp, checksum, setup_logging
from api_client import ApiClient
from config import api_base_url, api_config_path, device_id, serial_number, location_latitude, location_longitude, timezone

def main():
    setup_logging()

    argparser = argparse.ArgumentParser()
    argparser.add_argument("files", type=str, nargs="+")
    args = argparser.parse_args()

    client = ApiClient(api_base_url, api_config_path)

    file_ids = sorted(list(set([os.path.splitext(os.path.basename(f))[0] for f in args.files])))
    
    for file_id in tqdm(file_ids):
        paths = [path for path in args.files if os.path.splitext(os.path.basename(path))[0] == file_id]
        time = parse_raw_timestamp(file_id, timezone).isoformat()

        metadata = {
            "deviceID": device_id,
            "serialNumber": serial_number,
            "timestamp": {
                "start": time,
                "stop": time,
            },
            "location": {
                "latitude": location_latitude,
                "longitude": location_longitude,
                "geometry": {
                    "type": "Point",
                    "coordinates": [location_longitude, location_latitude],
                }
            },
            "files": [
                {
                "fileName": make_api_filename(p),
                "fileSize": os.path.getsize(p) * 1e-6,  # in megabytes (MB)
                "md5Checksum": checksum(p).hexdigest(),
                }
                for p in paths
            ],
            "sourceFiles": [],
        }

        file_handles = [open(p, "rb") for p in paths]
        client.upload_metadata(metadata, file_handles)
        [file_handle.close() for file_handle in file_handles]


if __name__ == "__main__":
    main()