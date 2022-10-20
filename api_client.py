from typing import IO, List
import os
import json
import logging
import io
import datetime
import time
import requests
from requests_toolbelt import MultipartEncoder

from config import api_user_agent

class ApiClient:
    """
    A class for communicating with the AMMOD API

    Attributes
    ----------
    config_path : str
        path to config file
    config_vars : list
        list of config variables to persist in the config file
    
    Methods
    -------
    load_config()
        loads configuration from the config file
    save_config()
        saves configuration in the config file
    refresh_token()
        refreshes API credentials
    upload_metadata(metadata, raw_data)
        uploads metadata with corresponding files
    search_metadata(params)
        searches metadata records according to params
    download_metadata(params, target_path, chunk_size)
        downloads metadata and associtated files according to params to target_path in chunk_sized chunks
    """

    def __init__(self, config_path: str, enable_logging=False) -> None:
        """
        Parameters
        ----------
        config_path : str
            path to config file
        enable_logging : bool, optional
            whether to enable logging (default is False)
        """

        if enable_logging:
            # setup logging
            requests_log = logging.getLogger("requests.packages.urllib3")
            requests_log.setLevel(logging.DEBUG)
            requests_log.propagate = True

        # load configuration from file
        self.config_path = config_path
        self.config_vars = ["base_url", "current_access_token", "current_refresh_token", "current_token_expiry"]
        self.load_config()

    def load_config(self):
        with open(self.config_path) as f:
            data = json.loads(f.read())
        for config_var in self.config_vars:
            setattr(self, config_var, data[config_var])

    def save_config(self):
        data = {config_var: getattr(self, config_var) for config_var in self.config_vars}
        with open(self.config_path, "w") as f:
            f.write(json.dumps(data, indent=4))

    def refresh_token(self):
        if datetime.datetime.strptime(self.current_token_expiry, "%Y-%m-%dT%H:%M:%SZ") <= datetime.datetime.now() - datetime.timedelta(hours=1):
            headers = {
                "x-access-token": self.current_refresh_token,
                "User-Agent": api_user_agent,
            }
            with requests.get(self.base_url + "/token/refresh", headers=headers) as r:

                # raise exception on HTTP error
                r.raise_for_status()

                data = r.json()

            # set new API credentials
            self.current_access_token = data["token"]
            self.current_refresh_token = data["refreshToken"]
            self.current_token_expiry = data["expiry"]

            # save new API credentials to disk
            self.save_config()

    def upload_metadata(self, metadata: dict, raw_data: List[IO]):
        """
        Parameters
        ----------
        metadata : dict
            the metadata to upload
        raw_data : list
            list of file objects to upload together with the metadata
        """

        if len(raw_data) == 0:
            raise ValueError("raw_data must contain at least one entry")
        if not "files" in metadata or len(raw_data) != len(metadata["files"]):
            raise ValueError("metadata.files must contain one entry for each raw_data entry")
        
        # refresh API token if expired
        self.refresh_token()

        # treat metadata as JSON file
        with io.StringIO(json.dumps(metadata)) as metadata_file:

            # use MultipartEncoder to handle large files without issues
            m = MultipartEncoder(fields={
                "file1": (os.path.splitext(metadata["files"][0]["fileName"])[0] + ".json", metadata_file),
                **{
                    f"file{i+2}": (api_file["fileName"], f)
                    for i, (api_file, f) in enumerate(zip(metadata["files"], raw_data))
                }
            })

            headers = {
                "x-access-token": self.current_access_token,
                "Content-Type": m.content_type,
                "User-Agent": api_user_agent,
            }
            with requests.post(self.base_url + "/metadata", data=m, headers=headers, timeout=None) as r:

                # raise exception on HTTP error
                r.raise_for_status()


    def search_metadata(self, params={}):
        """
        Parameters
        ----------
        params : dict
            parameters to search metadata by
        """

        # refresh API token if expired
        self.refresh_token()

        headers = {
            "x-access-token": self.current_access_token,
            "User-Agent": api_user_agent,
        }
        with requests.get(self.base_url + "/search/metadata", params=params, headers=headers) as r:

            # raise exception on HTTP error
            r.raise_for_status()

            return r.json()

    def download_metadata(self, params: dict, target_path: str, chunk_size=8192):
        """
        Parameters
        ----------
        params : dict
            parameters to download metadata by
        target_path : str
            path to the downloaded zip file
        chunk_size : int
            size of chunks written to disk at a time
        """

        # refresh API token if expired
        self.refresh_token()

        headers = {
            "x-access-token": self.current_access_token,
            "User-Agent": api_user_agent,
        }
        with requests.get(self.base_url + "/download/metadata", params={**params, "wait": False}, headers=headers) as r:
            r.raise_for_status()
            download_url = r.json()["url"]

        # loop until finished
        finished = False
        while not finished:
            with requests.get(download_url, stream=True) as r:

                # raise exception on HTTP error
                r.raise_for_status()

                # retry if file is not yet ready for download
                if r.status_code == 202:

                    # backoff to ensure API is not DOSed
                    time.sleep(30)

                    # retry
                    continue

                # download is starting
                with open(target_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size): 
                        f.write(chunk)

                # download is finished
                finished = True