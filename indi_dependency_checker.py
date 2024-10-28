#!/usr/bin/env python3

import subprocess
from pathlib import Path
from collections import defaultdict, deque
import shutil
import re
try:
    import git
except ModuleNotFoundError:
    print("Error: The 'gitPython' module is not installed. Please install it by running 'pip install gitPython'.")
    exit(1)

# Define the repository URL
repo_url = 'https://github.com/indilib/indi-3rdparty.git'
repo_path = Path.home() / 'indi-3rdparty'

# List of manually defined packages to ignore
ignored_packages = ["libapogee", "libindi-dev", "some_other_package"] 


def check_apt_cache_installed():
    """Check if apt-cache is available on the system."""
    if shutil.which("apt-cache") is None:
        print("Error: apt-cache is not installed or available on this system.")
        return False
    return True

# Check if git is installed
def check_git_installed():
    if shutil.which("git") is None:
        print("Error: Git is not installed. Please install Git and try again.")
        return False
    return True

# Clone or update the repository
def clone_or_update_repo(repo_url, destination_path):
    destination_path = Path(destination_path)
    try:
        if not destination_path.exists():
            print(f"Cloning {repo_url} into {destination_path}. This may take a few moments...")
            git.Repo.clone_from(repo_url, destination_path)
            print(f"Successfully cloned the repository.")
        else:
            print(f"Updating the repository at {destination_path}...")
            repo = git.Repo(destination_path)
            origin = repo.remotes.origin
            origin.pull()
            print(f"Repository is now up to date.")
        return True
    except Exception as e:
        print(f"Failed to clone or update the repository: {e}")
        return False

# List drivers in the 3rd-party repository
def list_drivers(drivers_directory_path):
    try:
        drivers = [item.name for item in drivers_directory_path.iterdir() if item.is_dir() and (item.name.startswith("indi-") or item.name.startswith("lib"))]
        return drivers
    except Exception as e:
        print(f"Error occurred while listing drivers: {e}")
        return []

# Fetch Debian drivers
def get_debian_drivers():
    try:
        result = subprocess.run(['apt-cache', 'search', 'indi-'], stdout=subprocess.PIPE, text=True, check=True)
        packages = [line.split()[0] for line in result.stdout.splitlines() if line.startswith('indi-') or line.startswith('lib')]
        return packages
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while fetching Debian drivers: {e}")
        return []

# Handle soname versions by keeping only the latest version
def handle_soname_versions(packages):
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

# Get Debian package version
def get_debian_version(package_name):
    try:
        result = subprocess.run(['apt-cache', 'policy', package_name], stdout=subprocess.PIPE, text=True, check=True)
        for line in result.stdout.splitlines():
            if 'Candidate:' in line:
                version = line.split()[1]
                cleaned_version = re.match(r'[\d\.]+', version)
                return cleaned_version.group(0) if cleaned_version else "Version not found"
        return "Version not found"
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while fetching version for {package_name}: {e}")
        return "Version not found"

# Extract version from changelog
def extract_version_from_changelog(changelog_path):
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

# Calculate version from Git hash if changelog is unavailable
def calculate_version_from_git_hash(repo_path):
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

def get_dependencies(package_name):
    """Retrieve the list of dependencies for a given package."""
    try:
        result = subprocess.run(['apt-cache', 'depends', package_name], stdout=subprocess.PIPE, text=True, check=True)
        dependencies = []
        for line in result.stdout.splitlines():
            if line.startswith("  Depends:"):
                dep = line.split("Depends:")[1].strip()
                dependencies.append(dep)
        return dependencies
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while fetching dependencies for {package_name}: {e}")
        return []

def sort_packages_by_dependencies(packages):
    """Sort packages based on dependencies using topological sort."""
    print("Sorting packages based on dependencies...")
    dependency_graph = defaultdict(list)
    indegree = defaultdict(int)

    for package in packages:
        dependencies = get_dependencies(package)
        for dep in dependencies:
            if dep in packages:
                dependency_graph[dep].append(package)
                indegree[package] += 1

    sorted_packages = []
    queue = deque([pkg for pkg in packages if indegree[pkg] == 0])

    while queue:
        pkg = queue.popleft()
        sorted_packages.append(pkg)
        for neighbor in dependency_graph[pkg]:
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                queue.append(neighbor)

    return sorted_packages

# Process each package
def process_package(package_name):
    debian_version = get_debian_version(package_name)
    repo_url = get_salsa_repo_url(package_name)
    repo_path = Path.home() / f"{package_name}-repo"
    if clone_or_update_repo(repo_url, repo_path):
        if debian_version == 'Version not found':
            version, git_hash = calculate_version_from_git_hash(repo_path)
            return version, git_hash
        else:
            git_hash = get_latest_git_hash(repo_path)
            return debian_version, git_hash
    else:
        print(f"Failed to process {package_name}")

# Print summary
if __name__ == "__main__":
    if check_git_installed():
        if clone_or_update_repo(repo_url, repo_path):
            drivers_directory_path = repo_path
            drivers_list = list_drivers(drivers_directory_path)

            if check_apt_cache_installed():
                debian_drivers = get_debian_drivers()
                debian_drivers = handle_soname_versions(debian_drivers)
                common_drivers = get_common_drivers(drivers_list, debian_drivers)
                
                sorted_common_drivers = sort_packages_by_dependencies(common_drivers)
                driver_results = {}

                for driver in sorted_common_drivers:

                    if driver in ignored_packages:
                        print(f"Ignoring {driver} as it is in the ignore list.")
                        continue  # Skip processing for ignored packages
                    
                    debian_version, debian_git_hash = process_package(driver)
                    driver_results[driver] = {
                        'version': debian_version,
                        'git_hash': debian_git_hash
                    }

                print(f"{'Driver':<25} | {'Version':<10} | {'Git Hash'}")
                print("-" * 60)

                for driver, details in driver_results.items():
                    print(f"{driver:<25} | {details['version']:<10} | {details['git_hash']}")
            else:
                print("Please install apt-cache to proceed. Using command 'sudo apt install apt-cache'")