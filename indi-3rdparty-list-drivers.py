#!/usr/bin/env python3

from pathlib import Path
import shutil
try:
    import git
except ModuleNotFoundError:
    print("Error: The 'gitPython' module is not installed. Please install it using 'apt install python3-git'.")
    exit(1)

repo_url = 'https://github.com/indilib/indi-3rdparty.git'
repo_path = Path.home() / 'indi-3rdparty'

# Function to clone or update the repository
def clone_or_update_repo(repo_url, destination_path):
    """
    Clone the repo if it's not already cloned, or perform a git pull if it already exists.
    
    Args:
        repo_url (str): URL of the repository.
        destination_path (Path): Path to clone the repository.
    
    Returns:
        bool: True if successful, False otherwise.
    """
    destination_path = Path(destination_path)
    print(f"Resolved destination path: {destination_path}")

    try:
        if not destination_path.exists():
            # Clone the repository if it doesn't exist
            print(f"Cloning {repo_url} into {destination_path}. This may take a few moments...")
            git.Repo.clone_from(repo_url, destination_path)
            print(f"Successfully cloned the repository into {destination_path}.")
        else:
            # Perform a git pull if the repository already exists
            print(f"Updating the repository at {destination_path}...")
            repo = git.Repo(destination_path)
            origin = repo.remotes.origin
            origin.pull()
            print(f"Repository at {destination_path} is now up to date.")
        
        return True
    except Exception as e:
        print(f"Failed to clone or update the repository: {e}")
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
        drivers = [item.name for item in drivers_directory_path.iterdir() if item.is_dir() and item.name.startswith("indi-") or item.name.startswith("lib")]
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

def calculate_version_from_git_hash(repo_path):
    """
    Calculate the version of the package based on the latest Git commit date and hash for the entire repository.
    
    Args:
        repo_path (Path): Path to the repository.
        driver (str): Not used in this context, we fetch the latest commit from the entire repository.
    
    Returns:
        tuple: The calculated version and the Git hash, or 'Version not found'.
    """
    try:
        repo = git.Repo(repo_path)

        # Getting the latest commit for the entire repository
        commit = next(repo.iter_commits(max_count=1))
        
        # Extracting the commit date and hash
        commit_date = commit.committed_datetime.strftime('%Y%m%d')
        git_hash = commit.hexsha

        base_version = extract_version_from_changelog(repo_path / 'debian' / 'changelog')
        if base_version == "Version not found":
            base_version = "1.0"
        
        version = f"{base_version}+git{commit_date}.{git_hash[:7]}"
        
        return version, git_hash
    except Exception as e:
        print(f"Error calculating version for the repository: {e}")
        return "Version not found", "Git hash not found"

    

if __name__ == "__main__":
    if check_git_installed():
        
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
                  # If version not found in changelog, calculate from Git hash and commit date
                    if version == "Version not found":
                        version, git_hash = calculate_version_from_git_hash(repo_path)
                    else:
                        # Get the Git hash if version is found in the changelog
                        git_hash = get_git_hash(repo_path, driver)
                    
                    print(f"{driver:<25} | {version:<20} | {git_hash}")
            
            else:
                print("No drivers found or an error occurred.")