import os
import datetime
import hashlib
import pytz
import logging

def parse_raw_timestamp(raw_timestamp: str, timezone_name: str):
    return datetime.datetime.strptime(raw_timestamp, r"%Y%m%d%H%M%S").replace(tzinfo=pytz.timezone(timezone_name))

def make_api_filename(original_filename: str):
    return f"Lindenthal-Zoo-RGBD-{os.path.basename(original_filename)}"

def parse_api_filename(api_filename: str):
    return parse_raw_timestamp(os.path.splitext(api_filename)[0].split("-")[-1])

def step_name_to_docker_name(step_name: str):
    return f"ammod-interface/{step_name}"

def checksum(filename, hash_factory=hashlib.md5, chunk_num_blocks=128):
    h = hash_factory()
    with open(filename, "rb") as f: 
        for chunk in iter(lambda: f.read(chunk_num_blocks * h.block_size), b""): 
            h.update(chunk)
    return h

def setup_logging():
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)