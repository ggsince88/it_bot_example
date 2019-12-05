# Authentication
1. Generate service credentials from the Google Developer Console with the appropriate permissions.
2. Download JSON file with credentials and place in this directory with a file name of `service_secret.json`.
3. When the docker-compose.yml runs it will copy all contents of this directory and `gsuitecmds.py` will reference be able to access `service_secret.json`
