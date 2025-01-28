from playwright.sync_api import sync_playwright
import zipfile
import os
import subprocess
import shutil

def download_zip_with_playwright(download_page_url, download_dir):
    """Uses Playwright to automate downloading a zip file from the given page URL."""
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            print("Navigating to the download page...")
            page.goto(download_page_url)

            with page.expect_download() as download_info:
                print("Initiating download...")

            download = download_info.value
            print("Saving download...")
            download.save_as(os.path.join(download_dir, download.suggested_filename))
        except Exception as e:
            print(f"Error downloading zip file: {e}")
        
        finally:
            browser.close()

def extract_zip(zip_file_path, extract_to):
    """Extracts the given zip file to the specified directory."""
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

def merge_files_in_directory(directory, output_file):
    """Merges the content of all files in the given directory into one file with separation."""
    with open(output_file, 'w', encoding='utf-8') as outfile:
        first_file = True
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as infile:
                    if not first_file:
                        outfile.write('\n\n')  # Add two newlines for separation
                    outfile.write(infile.read())
                    first_file = False

def remove_initial_newlines(output_file):
    """Removes initial newlines from the output file."""
    with open(output_file, 'r+', encoding='utf-8') as file:
        content = file.read().lstrip('\n')
        file.seek(0)
        file.write(content)
        file.truncate()

if __name__ == "__main__":
    github_url = "https://github.com/reflex-dev/reflex-web/tree/main/docs"
    download_page_url = f"https://download-directory.github.io/?url={github_url}"
    download_dir = "downloads"
    extraction_path = "extracted_files"
    output_file_name = "reflex_docs.txt"

    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    print("Downloading zip file...")
    download_zip_with_playwright(download_page_url, download_dir)

    # Find the downloaded zip file
    zip_file_path = None
    for file in os.listdir(download_dir):
        if file.endswith('.zip'):
            zip_file_path = os.path.join(download_dir, file)
            break

    if not zip_file_path:
        raise Exception("No zip file found in the download directory.")

    print("Extracting zip file...")
    extract_zip(zip_file_path, extraction_path)

    print("Merging files...")
    merge_files_in_directory(extraction_path, output_file_name)

    print(f"All files merged into {output_file_name}.")

    # Remove initial newlines from the output file
    remove_initial_newlines(output_file_name)

    # Clean up downloaded and extracted files
    shutil.rmtree(download_dir)
    shutil.rmtree(extraction_path)
