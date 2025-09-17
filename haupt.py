import os
import shutil
import requests
import logging
import base64
from typing import List, Dict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

GITHUB_REPO_OWNER = "reflex-dev"
GITHUB_REPO_NAME = "reflex-web"
DOCS_PATH = "docs"  # Path within the repo to fetch


def _github_api_headers() -> Dict[str, str]:
    """Return headers for GitHub API requests, using token if provided."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_directory_contents(path: str) -> List[Dict]:
    """Fetch directory listing from GitHub API."""
    url = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/contents/{path.strip('/') }"
    logging.info(f"Fetching directory listing: {url}")
    resp = requests.get(url, headers=_github_api_headers(), timeout=30)
    try:
        resp.raise_for_status()
    except Exception as e:
        logging.error(f"Failed to fetch directory listing for {path}: {e} (status {resp.status_code})")
        raise
    data = resp.json()
    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected API response for path {path}: {data}")
    return data


def fetch_file_content(item: Dict) -> str:
    """Fetch the text content of a file item from GitHub. Handles base64 if needed."""
    download_url = item.get("download_url")
    if download_url:
        logging.debug(f"Downloading raw file: {download_url}")
        resp = requests.get(download_url, headers=_github_api_headers(), timeout=30)
        resp.raise_for_status()
        return resp.text
    # Fallback to content field (base64)
    api_url = item.get("url")
    if not api_url:
        raise RuntimeError(f"File item missing URL: {item}")
    resp = requests.get(api_url, headers=_github_api_headers(), timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if data.get("encoding") == "base64" and "content" in data:
        return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    if isinstance(data, dict) and "content" in data and isinstance(data.get("content"), str):
        # Some APIs might deliver raw (non-base64) content; attempt straightforward return.
        return data["content"]
    raise RuntimeError(f"Unable to obtain content for file: {item.get('path')}")


def collect_docs(temp_dir: str) -> List[str]:
    """Recursively collect documentation files from the GitHub repository into temp_dir.

    Returns a list of file paths (local) saved.
    """
    saved_files: List[str] = []

    def recurse(current_path: str):
        try:
            listing = fetch_directory_contents(current_path)
        except Exception:
            return
        for entry in listing:
            entry_type = entry.get("type")
            entry_path = entry.get("path")
            if not entry_path:
                continue
            if entry_type == "dir":
                recurse(entry_path)
            elif entry_type == "file":
                # Only process text-like files (skip images/binaries by extension)
                name_lower = entry_path.lower()
                if any(name_lower.endswith(ext) for ext in [".md", ".markdown", ".txt", ".rst", ".py"]):
                    try:
                        content = fetch_file_content(entry)
                        local_path = os.path.join(temp_dir, entry_path)
                        os.makedirs(os.path.dirname(local_path), exist_ok=True)
                        with open(local_path, "w", encoding="utf-8") as f:
                            f.write(content)
                        saved_files.append(local_path)
                        logging.info(f"Fetched file: {entry_path}")
                    except Exception as fe:
                        logging.warning(f"Failed to fetch file {entry_path}: {fe}")
                else:
                    logging.debug(f"Skipping non-text file: {entry_path}")
            else:
                logging.debug(f"Skipping unsupported entry type {entry_type} at {entry_path}")

    recurse(DOCS_PATH)
    return saved_files

def extract_zip(*_args, **_kwargs):  # Backwards compatibility placeholder
    raise NotImplementedError("Zip extraction no longer used; docs are fetched via GitHub API.")

def merge_files_in_directory(directory, output_file):
    """Merges the content of all files in the given directory into one file with separation."""
    logging.info(f"Merging files from {directory} into {output_file}")
    with open(output_file, 'w', encoding='utf-8') as outfile:
        first_file = True
        for root, _, files in os.walk(directory):
            for file_name in files:  # Renamed 'file' to 'file_name' to avoid conflict
                file_path = os.path.join(root, file_name)
                try:
                    with open(file_path, 'r', encoding='utf-8') as infile:
                        if not first_file:
                            outfile.write('\n\n')  # Add two newlines for separation
                        outfile.write(infile.read())
                        first_file = False
                except Exception as e:
                    logging.warning(f"Could not read file {file_path}: {e}")
    logging.info("File merging complete.")

def remove_initial_newlines(output_file):
    """Removes initial newlines from the output file."""
    logging.info(f"Removing initial newlines from {output_file}")
    with open(output_file, 'r+', encoding='utf-8') as file:
        content = file.read().lstrip('\n')
        file.seek(0)
        file.write(content)
        file.truncate()
    logging.info("Initial newlines removed.")

def check_for_changes(local_file, remote_url):
    """Checks if there are changes between the local file and the remote file."""
    logging.info(f"Checking for changes between {local_file} and {remote_url}")
    try:
        response = requests.get(remote_url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        remote_content = response.text
        with open(local_file, 'r', encoding='utf-8') as file:
            local_content = file.read()
        if local_content != remote_content:
            logging.info("Changes detected.")
            return True
        else:
            logging.info("No changes detected.")
            return False
    except requests.exceptions.RequestException as e:
        logging.warning(f"Failed to fetch remote file for change comparison: {e}")
        return True  # Assume changes if remote check fails, to be safe
    except IOError as e:
        logging.error(f"Could not read local file {local_file}: {e}")
        return True  # Assume changes if local file read fails

if __name__ == "__main__":
    # Direct GitHub repo details defined in constants above
    temp_docs_dir = "_downloaded_docs"
    output_file_name = "reflex_docs.txt"
    remote_file_url = "https://raw.githubusercontent.com/unfortunatelyalex/reflex-docs/refs/heads/main/reflex_docs.txt"

    logging.info("Starting documentation update process...")
    try:
        if not os.path.exists(temp_docs_dir):
            os.makedirs(temp_docs_dir)
            logging.info(f"Created temp docs directory: {temp_docs_dir}")

        logging.info("Fetching documentation files via GitHub API (no browser)...")
        fetched = collect_docs(temp_docs_dir)
        if not fetched:
            raise RuntimeError("No documentation files were fetched from the repository.")

        merge_files_in_directory(temp_docs_dir, output_file_name)
        remove_initial_newlines(output_file_name)

        if not check_for_changes(output_file_name, remote_file_url):
            logging.info("No changes found in the documentation content. Exiting.")
            # Clean up and exit if no changes
            if os.path.exists(temp_docs_dir):
                shutil.rmtree(temp_docs_dir)
            exit(0)
        else:
            logging.info("Documentation content has changed. Proceeding with commit.")

    except Exception as e:
        logging.critical(f"An error occurred during the script execution: {e}")
        # Ensure cleanup even on error before exiting
        if os.path.exists(temp_docs_dir):
            shutil.rmtree(temp_docs_dir)
        exit(1)  # Exit with error status
    finally:
        # Final cleanup, just in case it wasn't done (e.g. if exit(0) was called)
        logging.info("Ensuring temporary directories are cleaned up...")
        if os.path.exists(temp_docs_dir):
            shutil.rmtree(temp_docs_dir)
            logging.info(f"Removed directory: {temp_docs_dir}")

    logging.info("Script finished. Changes will be committed by the GitHub Action if any.")
