from dotenv import load_dotenv
import subprocess
import paramiko
import pexpect
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


LAST_BACKUP_DATABASE_DOWNLOAD_URL = os.getenv(
    'LAST_BACKUP_DATABASE_DOWNLOAD_URL') or ""
LAST_BACKUP_FILES_DOWNLOAD_URL = os.getenv(
    'LAST_BACKUP_FILES_DOWNLOAD_URL') or ""

# FILEMAKER
FILEMAKER_PASSWORD = os.getenv('FILEMAKER_PASSWORD') or ""

# ZIP
STORAGE_PATH = os.getenv('STORAGE_PATH') or "storage"
ZIP_PASSWORD = os.getenv('ZIP_PASSWORD') or ""
ZIP_STORAGE_PATH = os.getenv('ZIP_STORAGE_PATH') or ""
UNZIP = os.getenv('UNZIP') == "True"

# LOCAL (for curses support)
LOCAL = os.getenv('LOCAL') == "True"

# SSH Client
ssh_client = paramiko.SSHClient()
ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
stdscr = None
sftp = None

def argv_parser():
    # Parse command line arguments
    # Currently only one supported is "--backup-type" database|files

    backup_type = "database"

    type_flag_present = "--backup-type" in sys.argv
    if type_flag_present:
        type_flag_index = sys.argv.index("--backup-type")
        backup_type = sys.argv[type_flag_index + 1]

    if backup_type not in ["database", "files"]:
        print("Invalid backup type, must be one of database|files")
        sys.exit(1)

    return backup_type


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

    if LAST_BACKUP_DATABASE_DOWNLOAD_URL == "" and LAST_BACKUP_FILES_DOWNLOAD_URL == "":
        return False
    if UNZIP == True and ZIP_STORAGE_PATH == "":
        return False

    return True


def ensure_directory_exists(path):
    # Create the directory if it doesn't exist
    if not os.path.exists(path):
        os.makedirs(path)


def get_latest_backup_url():
    # Use the latest_download_url to fetch the .json file

    try:
        # Determine backup type
        backup_type = argv_parser()

        print(f"Downloading last .json of type {backup_type}")

        json_name = f"last_backup_{backup_type}.json"
        json_path = os.path.join(STORAGE_PATH, json_name)

        current_hash = ""
        # Get the current hash from our pre-existing json
        if os.path.exists(json_path):
            with open(json_path, 'r') as json_file:
                # Check if the file is a valid json
                hash = ""
                try:
                    hash = json.load(json_file)['hash']
                except json.JSONDecodeError as e:
                    print(f"Error reading json file: {e}")
                    print("Continuing with no hash")

                current_hash = hash

        download_url = LAST_BACKUP_DATABASE_DOWNLOAD_URL
        if backup_type == "files":
            download_url = LAST_BACKUP_FILES_DOWNLOAD_URL

        sftp.get(download_url, json_path)

        latest_backup = ""
        should_download = True

        # Parse the file and exrtact the latest backup url
        with open(json_path, 'r') as latest_backup_location:
            latest = latest_backup_location.read()
            try:
                # Read json file
                latest_backup = json.loads(latest)['location'] or ""

                if current_hash != "":
                    new_hash = json.loads(latest)['hash'] or ""
                    if new_hash == current_hash:
                        should_download = False
            except:
                print("Error reading json file, QUITTING...")
                sys.exit(1)

        if not should_download:
            print("No new backup available, QUITTING...")
            sys.exit(0)

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

        if LOCAL:
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

        if LOCAL:
            # Initialize curses
            stdscr = curses.initscr()
            curses.noecho()
            curses.cbreak()

        # Use the latest_download_url to fetch the .json file
        file_name = file_location.split("/")[-1]
        backup_type = argv_parser()

        storage_path = STORAGE_PATH
        if backup_type == "files":
            storage_path += "/files"
        else:
            storage_path += "/database"

        file_path = os.path.join(storage_path, file_name)
        sftp.get(file_location, file_path, callback=progress_callback)

        if LOCAL:
            # Restore terminal settings
            curses.echo()
            curses.nocbreak()
            curses.endwin()

        print(f"Backup downloaded as {file_name}.")

        return file_path
    except paramiko.SSHException as err:
        if LOCAL:
            curses.echo()
            curses.nocbreak()
            curses.endwin()

        print(f"Request failed with error: {err}")
        sys.exit(1)


def unzip_download(filepath):
    # Unzip the backup
    try:
        backup_type = argv_parser()
        rename = False
        if backup_type == "database":
            rename = True
        
        if rename:
            # Create temp dir to extract to
            temp_dir = os.path.join(STORAGE_PATH, "temp")
            archive_name = os.path.basename(filepath)
            without_extension = os.path.splitext(archive_name)[0]
            new_name = without_extension + ".fmp12"
            ensure_directory_exists(temp_dir)

            # Extract to temp dir
            subprocess.run(['7z', 'x', filepath, '-y',
                           f'-o{temp_dir}', f'-p{ZIP_PASSWORD}'], check=True)
            # Move all files to dir with archive_name, keep extension
            subprocess.run(['mv', f'{temp_dir}/*', f'{ZIP_STORAGE_PATH}/{new_name}'], check=True)
        else:
            # Extract straight to dir
            subprocess.run(['7z', 'x', filepath, '-y',
                           f'-o{ZIP_STORAGE_PATH}', f'-p{ZIP_PASSWORD}'], check=True)

        print(f"Backup unzipped in {ZIP_STORAGE_PATH}.")
    except subprocess.CalledProcessError as e:
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

def clean_storage_dirs():
    backup_type = argv_parser()
    # Clean up storage directory
    print("Cleaning up storage directory...")

    for root, dirs, files in os.walk(STORAGE_PATH):
        for file in files:
            # SKIP JSON
            if file.endswith(".json"):
                continue

            file_path = os.path.join(root, file)
            file_creation_time = os.path.getctime(file_path)

            # IF type is database only traverse database subdirectory
            if backup_type == "database" and "database" not in file_path:
                continue

            # IF type is files only traverse files subdirectory
            if backup_type == "files" and "files" not in file_path:
                continue

            if backup_type == "database":
                os.remove(file_path)
                print(f"Removed {file_path}.")
            else:
                # Older than 2 months
                if time.time() - file_creation_time > 5270000:
                    os.remove(file_path)
                    print(f"Removed {file_path}.")


def main():
    try:
        initialize_ssh_client()

        latest_backup_url = get_latest_backup_url()

        if not latest_backup_url or latest_backup_url == "":
            print("Latest backup url is empty, QUITTING...")
            sys.exit(1)

        backup_file_path = download_backup(latest_backup_url)

        if UNZIP:
            child = pexpect.spawn('fmsadmin CLOSE "MasterApp.fmp12" -ukuadmin')
            child.sendline('y')
            child.expect("password:")
            child.sendline(FILEMAKER_PASSWORD)
            child.expect(pexpect.EOF)
            print("DONE")
            print(child.before.decode())

            # Get filename
            archive_name = os.path.basename(backup_file_path)
            without_extension = os.path.splitext(archive_name)[0]
            new_name = without_extension + ".fmp12"
            full_new_path = os.path.join(ZIP_STORAGE_PATH, new_name)
            unzip_download(backup_file_path)

            # Succesful zip!
            # Remove zip
            backup_type = argv_parser()
            if backup_type == "database":
                os.remove(backup_file_path)

            subprocess.run(
                ['sh', '/home/kuadmin/dev/filemaker-nightly-backup-server/file_maker_set_rights.sh', f'-d{full_new_path}'])

            # Set database open
            print("SETTING OPEN")
            child = pexpect.spawn('fmsadmin OPEN "MasterApp.fmp12" -ukuadmin')
            child.sendline('y')
            child.expect("password:")
            child.sendline(FILEMAKER_PASSWORD)
            child.expect(pexpect.EOF)
            print("DONE")
            print(child.before.decode())

        # Cleanup
        clean_storage_dirs()

        print(ZIP_STORAGE_PATH)
        subprocess.run(
            ['sh', '/home/kuadmin/dev/filemaker-nightly-backup-server/clean_file_maker_dir.sh', f'-d{ZIP_STORAGE_PATH}'])
    finally:
        # Restore terminal settings
        try:
            if LOCAL:
                curses.echo()
                curses.nocbreak()
                curses.endwin()
        except:
            pass

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
