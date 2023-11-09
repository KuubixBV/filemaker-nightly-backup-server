from dotenv import load_dotenv
import paramiko
import zipfile
import curses
import json
import time
import sys
import os

dotenv_path = load_dotenv('.env')
# SFTP
SFTP_USERNAME = os.getenv('SFTP_USERNAME') or ""
SFTP_PASSWORD = os.getenv('SFTP_PASSWORD') or ""
SFTP_HOST = os.getenv('SFTP_HOST') or ""
SFTP_PORT = os.getenv('SFTP_PORT') or ""

LATEST_DOWNLOAD_URL = os.getenv('LATEST_DOWNLOAD_URL')
STORAGE_PATH = os.getenv('STORAGE_PATH') or "storage"

# ZIP
ZIP_PASSWORD = os.getenv('ZIP_PASSWORD') or ""
UNZIP = os.getenv('UNZIP') == "True"

# SSH Client
ssh_client = paramiko.SSHClient()
stdscr = None
sftp = None


def validate_environment_variables():
    # Validate environment variables
    if SFTP_USERNAME == "":
        return False

    if SFTP_PASSWORD == "":
        return False

    if SFTP_HOST == "":
        return False

    if SFTP_PORT == "":
        return False

    if LATEST_DOWNLOAD_URL == "":
        return False

    return True


def ensure_directory_exists(path):
    # Create the directory if it doesn't exist
    if not os.path.exists(path):
        os.makedirs(path)


def get_latest_backup_url():
    # Use the latest_download_url to fetch the .json file

    try:
        print("Downloading last backup.json")
        json_path = os.path.join(STORAGE_PATH, "last_backup.json")
        print(json_path)
        print(LATEST_DOWNLOAD_URL)
        sftp.get(LATEST_DOWNLOAD_URL, json_path)

        latest_backup = ""
        # Parse the file and exrtact the latest backup url
        with open(json_path, 'r') as latest_backup_location:
            latest = latest_backup_location.read()
            # Read json file
            latest_backup = json.loads(latest)['location'] or ""

        print(f"Last backup location is {latest_backup}")
        return latest_backup

        # return latest_download_json['latest_backup'] or ""
    except paramiko.SSHException as err:
        print(f"Request failed with error: {err}")
        sys.exit(1)


def progress_callback(transferred, total):
    # Display progress

    progress_callback.last_call = getattr(progress_callback, 'last_call', 0)
    progress_callback.start_time = getattr(
        progress_callback, 'start_time', time.time())

    percent_complete = transferred / total * 100

    # Only update the screen if the percent_complete has changed by 0.1
    if percent_complete - progress_callback.last_call >= 0.1:
        elapsed_time = time.time() - progress_callback.start_time
        speed = transferred / elapsed_time
        estimated_total_time = total / speed
        estimated_time_remaining = estimated_total_time - elapsed_time
        estimated_time_minutes = (
            estimated_time_remaining // 60) + (estimated_time_remaining % 60) / 100

        # Download speed kb/s
        speed_kb_s = speed / 1024

        if speed_kb_s > 1024:
            speed = speed_kb_s / 1024
            speed_unit = "MB/s"
        else:
            speed = speed_kb_s
            speed_unit = "KB/s"

        stdscr.addstr(0, 0,
                      f"Transferred: {transferred}/{total} bytes ({percent_complete:.2f}%)")
        stdscr.addstr(1, 0,
                      f"Estimated Time Remaining (minutes): {estimated_time_minutes:.1f}")
        stdscr.addstr(2, 0,
                      f"Estimated Time Remaining (seconds): {estimated_time_remaining:.1f}")
        stdscr.addstr(3, 0, f"Download Speed: {speed:.2f}{speed_unit}")
        stdscr.refresh()

        progress_callback.last_call = percent_complete


def download_backup(file_location):
    # Download the backup
    global stdscr
    try:
        print("Downloading backup...")

        # Initialize curses
        stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()

        # Use the latest_download_url to fetch the .json file
        file_name = file_location.split("/")[-1]
        file_path = os.path.join(STORAGE_PATH, file_name)
        sftp.get(file_location, file_path, callback=progress_callback)

        # Restore terminal settings
        curses.echo()
        curses.nocbreak()
        curses.endwin()

        print(f"Backup downloaded as {file_name}.")

        return file_path
    except paramiko.SSHException as err:
        curses.echo()
        curses.nocbreak()
        curses.endwin()

        print(f"Request failed with error: {err}")
        sys.exit(1)


def unzip_download(filepath):
    # Unzip the backup

    try:
        with zipfile.ZipFile(filepath, 'r') as zip_ref:
            zip_ref.extractall(STORAGE_PATH, pwd=bytes(ZIP_PASSWORD, 'utf-8'))
        print(f"Backup unzipped in {STORAGE_PATH}.")
    except zipfile.BadZipFile as e:
        print(f"Error unzipping: {e}")
        sys.exit(1)


def initialize_ssh_client():
    # Initialize the ssh client

    global sftp
    print("Initializing ssh client...")
    ssh_client.load_system_host_keys()
    ssh_client.connect(
        hostname=SFTP_HOST,
        port=SFTP_PORT,
        username=SFTP_USERNAME,
        password=SFTP_PASSWORD
    )
    print("SSH client initialized.")

    print("Opening sftp connection...")
    sftp = ssh_client.open_sftp()
    print("Sftp connection opened.")


def main():
    try:
        initialize_ssh_client()

        latest_backup_url = get_latest_backup_url()

        if not latest_backup_url or latest_backup_url == "":
            print("Latest backup url is empty, QUITTING...")
            sys.exit(1)

        backup_file_path = download_backup(latest_backup_url)

        if UNZIP:
            unzip_download(backup_file_path)

        pass
    finally:
        # Restore terminal settings
        curses.echo()
        curses.nocbreak()
        curses.endwin()

        # make sure to always close the connections
        print("Closing connections...")
        if sftp:
            sftp.close()
        ssh_client.close()


if __name__ == "__main__":
    if not validate_environment_variables():
        print("Validation failed, check .env")
        sys.exit(1)

    ensure_directory_exists(STORAGE_PATH)
    main()
