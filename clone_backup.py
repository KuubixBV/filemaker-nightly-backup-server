from dotenv import load_dotenv
import requests
import zipfile
import sys
import os

load_dotenv()
LATEST_DOWNLOAD_URL = os.getenv('LATEST_DOWNLOAD_URL')
UNZIP_DOWNLOAD = os.getenv('UNZIP_DOWNLOAD') == "True"
STORAGE_PATH = os.getenv('STORAGE_PATH') or "storage"


def validate_environment_variables():
    if LATEST_DOWNLOAD_URL == "":
        return False

    return True


def ensure_directory_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)


def get_latest_backup_url():
    try:
        # Use the latest_download_url to fetch the .json file
        response = requests.get(LATEST_DOWNLOAD_URL)
        response.reaise_for_status()

        # Parse the file and exrtact the latest backup url
        latest_download_json = response.json()
        return latest_download_json['latest_backup'] or ""
    except requests.exceptions.HTTPError as err:
        print(f"Request failed with error: {err}")
        sys.exit(1)


def download_backup(file_location):
    try:
        # Use the latest_download_url to fetch the .json file
        response = requests.get(file_location)
        response.reaise_for_status()

        filename = os.path.basename(file_location)
        filepath = os.path.join(STORAGE_PATH, filename)
        with open(filepath, 'wb') as f:
            f.write(response.content)

        print(f"Backup downloaded as {filename}.")
        return filepath
    except requests.exceptions.HTTPError as err:
        print(f"Request failed with error: {err}")
        sys.exit(1)


def unzip_download(filepath):
    try:
        with zipfile.ZipFile(filepath, 'r') as zip_ref:
            zip_ref.extractall(STORAGE_PATH)
        print(f"Backup unzipped in {STORAGE_PATH}.")
    except zipfile.BadZipFile as e:
        print(f"Error unzipping: {e}")
        sys.exit(1)


def main():
    if not validate_environment_variables():
        print("Latest backup url is empty, QUITTING...")
        sys.exit(1)

    latest_backup_url = get_latest_backup_url()

    if not latest_backup_url:
        print("Latest backup url is empty, QUITTING...")
        sys.exit(1)

    backup_file_path = download_backup(latest_backup_url)

    if UNZIP_DOWNLOAD:
        unzip_download(backup_file_path)


if __name__ == "__main__":
    ensure_directory_exists()
    main()
