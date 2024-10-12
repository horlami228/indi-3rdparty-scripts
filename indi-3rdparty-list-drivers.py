#!/usr/bin/env python3

from pathlib import Path
import git
import shutil

def clone_or_update_repo(repo_url, destination_path):
    """
    Clone the repo if it's not already cloned, or perform a git pull if it already exists.
    
    Args:
        repo_url (str): URL of the repository.
        destination_path (Path): Path to clone the repository.
    
    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        if not destination_path.exists():
            # Clone the repository if it doesn't exist
            git.Repo.clone_from(repo_url, destination_path)
        else:
            repo = git.Repo(destination_path)
            origin = repo.remotes.origin
            origin.pull()
        return True
    except Exception as e:
        print(f"Failed to clone or update repository: {e}")
        return False

# Function to check if git is installed
def check_git_installed():
    """Check if git is available on the system."""
    if shutil.which("git") is None:
        print("Error: Git is not installed. Please install Git and try again.")
        return False
    return True

# Function to list drivers from the 3rdparty repository
def list_drivers(drivers_directory_path):
    """List all the drivers in the repository.
        Args: drivers_directory_path (Path): Path to the drivers directory.
    """
    try:
        drivers = [item.name for item in drivers_directory_path.iterdir() if item.is_dir() and item.name.startswith("indi-")]
        return drivers
    except Exception as e:
        print(f"Error occurred while listing drivers: {e}")
        return []

def extract_version_from_changelog(changelog_path):
    """
    Extract the driver version from the changelog file.
    Args:
        changelog_path (Path): Path to the changelog file.
    Returns:
        str: Extracted version, or 'Version not found'.
    """
    if changelog_path.exists():
        try:
            with changelog_path.open() as changelog_file:
                # The version is typically found in the first line in parentheses
                first_line = changelog_file.readline().strip()
                if first_line:
                    version = first_line.split()[1].strip("()")
                    return version
        except Exception as e:
            print(f"Error reading version from {changelog_path}: {e}")
    return "Version not found"
    
def get_git_hash(repo_path, driver_path):
    """Get the latest git hash of a driver using gitpython."""
    try:
        repo = git.Repo(repo_path)
        driver_repo_path = str(repo_path / driver_path)
        latest_commit = next(repo.iter_commits(paths=driver_repo_path, max_count=1))
        return latest_commit.hexsha
    except Exception as e:
        print(f"Error fetching git hash for {driver_path}: {e}")
        return "Git hash not found"


repo_url = 'https://github.com/indilib/indi-3rdparty.git'
repo_path = Path.home() / 'indi-3rdparty'

if __name__ == "__main__":
    if check_git_installed():
        repo_url = 'https://github.com/indilib/indi-3rdparty.git'
        repo_path = Path.home() / 'indi-3rdparty'
        
        # Clone the repository if it doesn't exist
        if clone_or_update_repo(repo_url, repo_path):
            drivers_directory_path = repo_path
            
            # List drivers
            drivers_list = list_drivers(drivers_directory_path)

            # Print header
            print(f"{'Driver':<25} | {'Version':<10} | {'Git Hash'}")
            print("-" * 60)

            if drivers_list:
                for driver in drivers_list:
                    # Get the changelog path for each driver
                    changelog_path = drivers_directory_path / 'debian' / driver / 'changelog'
                    version = extract_version_from_changelog(changelog_path)
                    git_hash = get_git_hash(repo_path, driver)
                    print(f"{driver:<25} | {version:<10} | {git_hash}")
            else:
                print("No drivers found or an error occurred.")