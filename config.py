# identifiers of the source sensor
device_id = 8310  # for production instance
# device_id = 7980  # for staging instance

serial_number = "d49a6930-7ab7-450f-afad-c38cff2f8109"

# geographic location of the source sensor
location_latitude = 50.712807
location_longitude = 7.090508

# timezone of the source sensor
timezone = "Europe/Berlin"

# base URL of the API
api_base_url = "https://ammod.gfbio.dev/api/v1"

# relative or absolute path to the API config file
api_config_path = "api_config.json"

# HTTP user agent for communication with the API
api_user_agent = "Module 2.3 Interface (https://github.com/ammod-ubn/ammod-portal-interface)"

# time to wait between repeated API calls in seconds
api_poll_period = 30

# whether the generated data is usable for research purposes
usable_for_research = True