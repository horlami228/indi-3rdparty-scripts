#!/usr/bin/env python3

import subprocess
from pathlib import Path
import shutil
import re
try:
    import git
except ModuleNotFoundError:
    print("Error: The 'gitPython' module is not installed. Please install it by running 'pip install gitPython'.")
    exit(1)

repo_url = 'https://github.com/indilib/indi-3rdparty.git'
repo_path = Path.home() / 'indi-3rdparty'

def check_apt_cache_installed():
    """Check if apt-cache is available on the system."""
    if shutil.which("apt-cache") is None:
        print("Error: apt-cache is not installed or available on this system.")
        return False
    return True

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
        drivers = [item.name for item in drivers_directory_path.iterdir() if item.is_dir() and item.name.startswith("indi-")]
        return drivers
    except Exception as e:
        print(f"Error occurred while listing drivers: {e}")
        return []

def get_debian_drivers():
    """
    Get a list of INDI drivers available as Debian packages.
    
    Returns:
        list: A list of package names matching 'indi-*'.
    """
    try:
        result = subprocess.run(['apt-cache', 'search', 'indi-'], stdout=subprocess.PIPE, text=True, check=True)
        # Filter lines that start with 'indi-' to get package names
        packages = [line.split()[0] for line in result.stdout.splitlines() if line.startswith('indi-')]
        return packages
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while fetching Debian drivers: {e}")
        return []
    
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

def get_common_drivers(indi_third_party_drivers, debian_drivers):
    """Get drivers that are available in both the 3rd-party repository and Debian packages.
       Args:
           indi_third_party_drivers (list): List of drivers from the 3rd-party repo.
           debian_drivers (list): List of drivers available as Debian packages.
       Returns:
           list: Drivers found in both 3rd-party and Debian.
    """
    debian_set = set(debian_drivers)
    third_party_set = set(indi_third_party_drivers)
    common_drivers = third_party_set.intersection(debian_set)
    return list(common_drivers)

def get_debian_version(package_name):
    """
    Get the version of a specific Debian package, cleaning the version to remove timestamps and unnecessary suffixes.
    
    Args:
        package_name (str): The name of the Debian package.
    
    Returns:
        str: Cleaned version of the package or 'Version not found' if package not found.
    """
    try:
        result = subprocess.run(['apt-cache', 'policy', package_name], stdout=subprocess.PIPE, text=True, check=True)
        for line in result.stdout.splitlines():
            if 'Candidate:' in line:
                version = line.split()[1]
                # Regular expression to match the version part (before the timestamp or other suffixes)
                cleaned_version = re.match(r'[\d\.]+', version)
                return cleaned_version.group(0) if cleaned_version else "Version not found"
        return "Version not found"
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while fetching version for {package_name}: {e}")
        return "Version not found"

def get_salsa_repo_url(package_name):
    """
    Construct a potential Salsa repository URL based on the package name.
    Args:
        package_name (str): The name of the Debian package.
    
    Returns:
        str: The constructed Salsa Git repository URL.
    """
    return f"https://salsa.debian.org/debian-astro-team/{package_name}.git"

def get_latest_git_hash(repo_path):
    """
    Get the latest git hash of a cloned repository.
    Args:
        repo_path (Path): The path to the cloned repository.
    
    Returns:
        str: The latest git hash or an error message.
    """
    try:
        repo = git.Repo(repo_path)
        latest_commit = repo.head.commit.hexsha
        return latest_commit
    except Exception as e:
        print(f"Error fetching git hash for {repo_path}: {e}")
        return "Git hash not found"

def process_package(package_name):
    # Step 1: Construct the Git URL
    repo_url = get_salsa_repo_url(package_name)
    
    # Step 2: Define the local path to clone the repository
    repo_path = Path.home() / f"{package_name}-repo"
    
    # Step 3: Clone the repository if not already cloned
    if clone_or_update_repo(repo_url, repo_path):
        
        # Step 4: Get the latest Git hash
        git_hash = get_latest_git_hash(repo_path)
        return git_hash
    else:
        print(f"Failed to process {package_name}")




if __name__ == "__main__":
    if check_git_installed():
        # Clone the repository if it doesn't exist
        if clone_or_update_repo(repo_url, repo_path):
            drivers_directory_path = repo_path

            # List drivers
            drivers_list = list_drivers(drivers_directory_path)

            if check_apt_cache_installed():
                # list debian drivers
                debian_drivers = get_debian_drivers()

                # Get common drivers
                common_drivers = get_common_drivers(drivers_list, debian_drivers)
                
                driver_results = {}

                # Get the driver version
                for driver in common_drivers:
                    debian_version = get_debian_version(driver)
                    debian_git_hash = process_package(driver)

                                        # Save results in dictionary
                    driver_results[driver] = {
                        'version': debian_version,
                        'git_hash': debian_git_hash
                    }

                # Print header
                print(f"{'Driver':<25} | {'Version':<10} | {'Git Hash'}")
                print("-" * 60)

                for driver, details in driver_results.items():
                    print(f"{driver:<25} | {details['version']:<10} | {details['git_hash']}")
            else:
                print("Please install apt-cache to proceed.")

