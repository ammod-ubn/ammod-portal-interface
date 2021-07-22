from typing import IO, List
import json
import logging
import io
import datetime
import time
import requests
from requests_toolbelt import MultipartEncoder

from config import api_user_agent

class ApiClient:
    def __init__(self, base_url: str, config_path: str, enable_logging=False) -> None:
        self.base_url = base_url
        if enable_logging:
            requests_log = logging.getLogger("requests.packages.urllib3")
            requests_log.setLevel(logging.DEBUG)
            requests_log.propagate = True
        self.config_path = config_path
        self.config_vars = ["current_access_token", "current_refresh_token", "current_token_expiry"]
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
                r.raise_for_status()
                data = r.json()
            self.current_access_token = data["token"]
            self.current_refresh_token = data["refreshToken"]
            self.current_token_expiry = data["expiry"]
            self.save_config()

    def upload_metadata(self, metadata: dict, raw_data: List[IO]):
        if len(raw_data) == 0:
            raise ValueError("raw_data must contain at least one entry")
        if not "files" in metadata or len(raw_data) != len(metadata["files"]):
            raise ValueError("metadata.files must contain one entry for each raw_data entry")
        
        self.refresh_token()
        with io.StringIO(json.dumps(metadata)) as metadata_file:
            m = MultipartEncoder(fields={
                "file1": ("metadata.json", metadata_file),
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
                r.raise_for_status()

    def search_metadata(self, params={}):
        self.refresh_token()
        headers = {
            "x-access-token": self.current_access_token,
            "User-Agent": api_user_agent,
        }
        with requests.get(self.base_url + "/search/metadata", params=params, headers=headers) as r:
            r.raise_for_status()
            return r.json()

    def download_metadata(self, params: dict, target_path: str, chunk_size=8192):
        self.refresh_token()
        headers = {
            "x-access-token": self.current_access_token,
            "User-Agent": api_user_agent,
        }
        with requests.get(self.base_url + "/download/metadata", params={**params, "wait": False}, headers=headers) as r:
            r.raise_for_status()
            download_url = r.json()["url"]
        finished = False
        while not finished:
            with requests.get(download_url, stream=True) as r:
                r.raise_for_status()
                if r.status_code == 202:
                    time.sleep(30)
                    continue
                finished = True
                with open(target_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size): 
                        f.write(chunk)