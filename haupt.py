from playwright.sync_api import sync_playwright
import zipfile
import os
import subprocess
import shutil
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def download_zip_with_playwright(download_page_url, download_dir):
    """Uses Playwright to automate downloading a zip file from the given page URL."""
    with sync_playwright() as p:
        browser = None  # Initialize browser to None
        try:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            logging.info(f"Navigating to the download page: {download_page_url}")
            page.goto(download_page_url)

            with page.expect_download() as download_info:
                logging.info("Initiating download...")

            download = download_info.value
            download_path = os.path.join(download_dir, download.suggested_filename)
            logging.info(f"Saving download to {download_path}")
            download.save_as(download_path)
        except Exception as e:
            logging.error(f"Error downloading zip file: {e}")
            raise  # Re-raise to allow main script to handle

        finally:
            if browser:
                browser.close()

def extract_zip(zip_file_path, extract_to):
    """Extracts the given zip file to the specified directory."""
    logging.info(f"Extracting {zip_file_path} to {extract_to}")
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    logging.info("Extraction complete.")

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
    github_url = "https://github.com/reflex-dev/reflex-web/tree/main/docs"
    download_page_url = f"https://download-directory.github.io/?url={github_url}"
    download_dir = "downloads"
    extraction_path = "extracted_files"
    output_file_name = "reflex_docs.txt"
    remote_file_url = "https://raw.githubusercontent.com/unfortunatelyalex/reflex-docs/refs/heads/main/reflex_docs.txt"

    logging.info("Starting documentation update process...")
    try:
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
            logging.info(f"Created download directory: {download_dir}")

        logging.info("Downloading zip file...")
        download_zip_with_playwright(download_page_url, download_dir)

        zip_file_path = None
        for file in os.listdir(download_dir):
            if file.endswith('.zip'):
                zip_file_path = os.path.join(download_dir, file)
                logging.info(f"Found zip file: {zip_file_path}")
                break

        if not zip_file_path:
            logging.error("No zip file found in the download directory.")
            raise Exception("No zip file found in the download directory.")

        if not os.path.exists(extraction_path):
            os.makedirs(extraction_path)
            logging.info(f"Created extraction directory: {extraction_path}")

        extract_zip(zip_file_path, extraction_path)
        merge_files_in_directory(extraction_path, output_file_name)
        remove_initial_newlines(output_file_name)

        if not check_for_changes(output_file_name, remote_file_url):
            logging.info("No changes found in the documentation content. Exiting.")
            # Clean up and exit if no changes
            if os.path.exists(download_dir):
                shutil.rmtree(download_dir)
            if os.path.exists(extraction_path):
                shutil.rmtree(extraction_path)
            exit(0)
        else:
            logging.info("Documentation content has changed. Proceeding with commit.")

    except Exception as e:
        logging.critical(f"An error occurred during the script execution: {e}")
        # Ensure cleanup even on error before exiting
        if os.path.exists(download_dir):
            shutil.rmtree(download_dir)
        if os.path.exists(extraction_path):
            shutil.rmtree(extraction_path)
        exit(1)  # Exit with error status
    finally:
        # Final cleanup, just in case it wasn't done (e.g. if exit(0) was called)
        logging.info("Ensuring temporary directories are cleaned up...")
        if os.path.exists(download_dir):
            shutil.rmtree(download_dir)
            logging.info(f"Removed directory: {download_dir}")
        if os.path.exists(extraction_path):
            shutil.rmtree(extraction_path)
            logging.info(f"Removed directory: {extraction_path}")

    logging.info("Script finished. Changes will be committed by the GitHub Action if any.")
