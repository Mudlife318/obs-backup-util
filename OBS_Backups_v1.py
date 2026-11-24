import obspython as obs
import os
import shutil
import datetime
import time
import threading

# Global variables
folder_path = ""
backup_interval_days = 7  # Default backup interval
retention_days = 30       # Default retention period
automatic_backups_enabled = False
backup_thread = None

# OBS configuration path for Windows
obs_config_path = os.path.join(os.getenv('APPDATA'), 'obs-studio')

# Create a new timestamped folder
def create_timestamped_folder(base_path):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return os.path.join(base_path, f"backup_{timestamp}")

# Copy directories manually if they exist
def copy_directory(src, dst):
    if os.path.exists(dst):
        shutil.rmtree(dst)  # Remove existing directory to avoid conflicts
    shutil.copytree(src, dst)

# Backup process
def perform_backup():
    global folder_path
    global obs_config_path

    if not folder_path:
        obs.script_log(obs.LOG_WARNING, "No folder selected for export!")
        return

    if not obs_config_path or not os.path.exists(obs_config_path):
        obs.script_log(obs.LOG_ERROR, f"OBS configuration path '{obs_config_path}' not found!")
        return

    try:
        # Paths to OBS scenes and profiles
        scenes_path = os.path.join(obs_config_path, "basic", "scenes")
        profiles_path = os.path.join(obs_config_path, "basic", "profiles")

        # Check if paths exist
        if not os.path.exists(scenes_path):
            obs.script_log(obs.LOG_ERROR, f"Scenes path '{scenes_path}' not found!")
            return
        if not os.path.exists(profiles_path):
            obs.script_log(obs.LOG_ERROR, f"Profiles path '{profiles_path}' not found!")
            return

        # Create a new timestamped folder for this backup
        backup_folder = create_timestamped_folder(folder_path)
        os.makedirs(os.path.join(backup_folder, "scenes"), exist_ok=True)
        os.makedirs(os.path.join(backup_folder, "profiles"), exist_ok=True)

        # Copy scenes and profiles
        copy_directory(scenes_path, os.path.join(backup_folder, "scenes"))
        copy_directory(profiles_path, os.path.join(backup_folder, "profiles"))

        obs.script_log(obs.LOG_INFO, f"Backup created successfully in {backup_folder}")
        manage_old_backups()
    except Exception as e:
        obs.script_log(obs.LOG_ERROR, f"Failed to export: {str(e)}")

# Manage old backups based on retention policy
def manage_old_backups():
    global folder_path
    if not folder_path:
        return

    now = datetime.datetime.now()
    for entry in os.listdir(folder_path):
        entry_path = os.path.join(folder_path, entry)
        if os.path.isdir(entry_path) and entry.startswith("backup_"):
            timestamp_str = entry[len("backup_"):]
            try:
                backup_date = datetime.datetime.strptime(timestamp_str, "%Y-%m-%d_%H-%M-%S")
                age_days = (now - backup_date).days
                if age_days > retention_days:
                    shutil.rmtree(entry_path)
                    obs.script_log(obs.LOG_INFO, f"Deleted old backup folder: {entry_path}")
            except ValueError:
                continue

# Automation loop in a separate thread
def backup_loop():
    while automatic_backups_enabled:
        perform_backup()
        time.sleep(backup_interval_days * 24 * 60 * 60)  # Sleep for the backup interval in seconds

# Function to handle folder selection
def on_folder_selected(props, prop):
    global folder_path
    folder_path = obs.obs_data_get_string(prop)

    if folder_path:
        obs.script_log(obs.LOG_INFO, f"Selected folder: {folder_path}")
    else:
        obs.script_log(obs.LOG_WARNING, "No folder selected!")

# Function to start/stop the backup loop based on checkbox state
def handle_automatic_backups():
    global automatic_backups_enabled
    global backup_thread

    if automatic_backups_enabled:
        if not backup_thread or not backup_thread.is_alive():
            backup_thread = threading.Thread(target=backup_loop, daemon=True)
            backup_thread.start()
    else:
        if backup_thread and backup_thread.is_alive():
            automatic_backups_enabled = False
            backup_thread.join()

# Function to update script settings
def script_update(settings):
    global folder_path
    global backup_interval_days
    global retention_days
    global automatic_backups_enabled

    folder_path = obs.obs_data_get_string(settings, "folder_path")
    backup_interval_days = obs.obs_data_get_int(settings, "backup_interval_days")
    retention_days = obs.obs_data_get_int(settings, "retention_days")
    automatic_backups_enabled = obs.obs_data_get_bool(settings, "automatic_backups_enabled")

    handle_automatic_backups()

# Function to set Script Description
def script_description():
    return (
        "Provides functionality for backing up OBS profiles, scenes, and settings.\n\n"
        "Tutorial:\n"
        "    Export Folder : Path to the folder where backups will be stored.\n"
        "    Backup Interval : Number of days between backups.\n"
        "    Retention Period : How long to store Backups before Deletion.\n\n"
        "Follow & Support Appreciated\n"
        "Twitch/Patreon: Mudlife318"
    )

# Script default settings
def script_defaults(settings):
    obs.obs_data_set_default_string(settings, "folder_path", "")
    obs.obs_data_set_default_int(settings, "backup_interval_days", 7)
    obs.obs_data_set_default_int(settings, "retention_days", 30)
    obs.obs_data_set_default_bool(settings, "automatic_backups_enabled", False)

# Function to define UI for the script
def script_properties():
    props = obs.obs_properties_create()

    # Add a folder path property for selecting the export folder
    obs.obs_properties_add_path(props, "folder_path", "Select Export Folder", obs.OBS_PATH_DIRECTORY, "", None)
    
    # Add properties for backup settings
    obs.obs_properties_add_int(props, "backup_interval_days", "Backup Interval (days)", 1, 365, 1)
    obs.obs_properties_add_int(props, "retention_days", "Retention Period (days)", 1, 365, 1)
    obs.obs_properties_add_bool(props, "automatic_backups_enabled", "Enable Automatic Backups")

    # Button to start the export process manually
    obs.obs_properties_add_button(props, "export_button", "Export Profiles and Scenes", export_profiles_and_scenes)

    return props

# Function to start the export process manually
def export_profiles_and_scenes(props, prop):
    perform_backup()
