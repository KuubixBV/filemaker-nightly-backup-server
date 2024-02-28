# filemaker-nightly-backup-server
Download the last backup on our server using SFTP.
Unzipping capabilities included.

## Configuration
Clone and modify the example env file
```
cp .env.example .env
nvim .env
```

## Installation
Create virtual environment and install dependencies
```
python3 -m venv backup_env
source backup_env/bin/activate
pip install -r requirements.txt
deactivate
```

## Run
```
sh run_backup.sh -t files
sh run_backup.sh -t database
```

