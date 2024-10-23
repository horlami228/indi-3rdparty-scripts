#!/usr/bin/env python3

from pathlib import Path
import shutil
import subprocess
import re
import git

# Repo URL and Path
repo_url = 'https://github.com/indilib/indi-3rdparty.git'
repo_path = Path.home() / 'indi-3rdparty'

# List of manually defined packages to ignore
ignored_packages = ["libapogee", "libindi-dev", "some_other_package"]  # Add any package to ignore

def clone_or_update_repo(repo_url, destination_path):
    """Clone the repo if it's not already cloned, or perform a git pull if it already exists."""
    destination_path = Path(destination_path)
    print(f"Resolved destination path: {destination_path}")

    try:
        if not destination_path.exists():
            print(f"Cloning {repo_url} into {destination_path}. This may take a few moments...")
            git.Repo.clone_from(repo_url, destination_path)
            print(f"Successfully cloned the repository into {destination_path}.")
        else:
            print(f"Updating the repository at {destination_path}...")
            repo = git.Repo(destination_path)
            origin = repo.remotes.origin
            origin.pull()
            print(f"Repository at {destination_path} is now up to date.")
        return True
    except Exception as e:
        print(f"Failed to clone or update the repository: {e}")
        return False
def get_salsa_repo_url(package_name):
    """
    Construct a potential Salsa repository URL based on the package name.
    Args:
        package_name (str): The name of the Debian package.
    
    Returns:
        str: The constructed Salsa Git repository URL.
    """
    return f"https://salsa.debian.org/debian-astro-team/{package_name}.git"

def check_git_installed():
    """Check if git is available on the system."""
    if shutil.which("git") is None:
        print("Error: Git is not installed. Please install Git and try again.")
        return False
    return True

def check_apt_cache_installed():
    """Check if apt-cache is available on the system."""
    if shutil.which("apt-cache") is None:
        print("Error: apt-cache is not installed or available on this system.")
        return False
    return True

def list_drivers(drivers_directory_path):
    """List all the drivers in the repository."""
    try:
        drivers = [item.name for item in drivers_directory_path.iterdir() if item.is_dir() and (item.name.startswith("indi-") or item.name.startswith("lib"))]
        return drivers
    except Exception as e:
        print(f"Error occurred while listing drivers: {e}")
        return []

def get_debian_drivers():
    """Get a list of INDI drivers available as Debian packages."""
    try:
        result = subprocess.run(['apt-cache', 'search', 'indi-'], stdout=subprocess.PIPE, text=True, check=True)
        packages = [line.split()[0] for line in result.stdout.splitlines() if line.startswith('indi-') or line.startswith('lib')]
        return packages
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while fetching Debian drivers: {e}")
        return []

def extract_version_from_changelog(changelog_path):
    """Extract the driver version from the changelog file."""
    if changelog_path.exists():
        try:
            with changelog_path.open() as changelog_file:
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
    """Calculate the version of the package based on the latest Git commit date and hash."""
    try:
        repo = git.Repo(repo_path)
        commit = next(repo.iter_commits(max_count=1))
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

def process_package(package_name):
    """Process a package to get its version and git hash."""
    repo_url = get_salsa_repo_url(package_name)
    repo_path = Path.home() / f"{package_name}-repo"

    if clone_or_update_repo(repo_url, repo_path):
        version, git_hash = calculate_version_from_git_hash(repo_path)
        return version, git_hash
    else:
        print(f"Failed to process {package_name}")

def handle_soname_versions(packages):
    """Handle soname versioning by keeping only the latest version of each package."""
    package_dict = {}
    for package in packages:
        base_name, _, version_suffix = package.rpartition('-')
        if not version_suffix.isdigit():
            base_name = package

        if base_name in package_dict:
            current_version = package_dict[base_name]
            if version_suffix.isdigit() and int(version_suffix) > int(current_version.rpartition('-')[-1]):
                package_dict[base_name] = package
        else:
            package_dict[base_name] = package
    return list(package_dict.values())

if __name__ == "__main__":
    if check_git_installed() and check_apt_cache_installed():
        if clone_or_update_repo(repo_url, repo_path):
            drivers_directory_path = repo_path
            drivers_list = list_drivers(drivers_directory_path)

            debian_drivers = get_debian_drivers()
            debian_drivers = handle_soname_versions(debian_drivers)

            common_drivers = set(drivers_list).intersection(set(debian_drivers))
            common_drivers = [driver for driver in common_drivers if driver not in ignored_packages]

            driver_results = {}
            for driver in common_drivers:
                version, git_hash = process_package(driver)
                driver_results[driver] = {
                    'version': version,
                    'git_hash': git_hash
                }

            print(f"{'Driver':<25} | {'Version':<10} | {'Git Hash'}")
            print("-" * 60)
            for driver, details in driver_results.items():
                print(f"{driver:<25} | {details['version']:<10} | {details['git_hash']}")
