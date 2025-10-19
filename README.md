# Reflex Docs Automation

This repository contains an automation script for merging the Reflex Documentation into one singular file. The automation is handled using GitHub Actions and Playwright to download, extract, and merge documentation files from the Reflex GitHub repository.

- Last checked: `2025-10-19 16:11:07 CEST`
- Last updated: `2025-10-18 06:11:30 CEST`

## Workflow

The automation workflow is defined in the `.github/workflows/reflex_docs.yml` file. It runs every 2 hours and can also be triggered manually. The workflow performs the following steps:
1. Checks out the repository.
2. Sets up Python 3.12.10
3. Installs necessary dependencies including Playwright.
4. Runs the automation script (`haupt.py`) to download, extract, and merge documentation files.
5. Checks if the merged content file has changed and if not no further action is taken.
6. Commits and pushes the changes to the repository with a commit message.

## Automation Script

The `haupt.py` script performs the following tasks:
1. Downloads a zip file containing the latest documentation from the Reflex GitHub repository using Playwright.
2. Extracts the zip file to a specified directory.
3. Merges the content of all extracted files into a single file (`reflex_docs.txt`), ensuring proper separation between file contents.
4. Removes any initial newlines from the merged content file.
5. Cleans up the downloaded and extracted files.

## How to Use

To manually trigger the workflow, navigate to the Actions tab in the GitHub repository and select the "Reflex Docs Automation" workflow. Click on the "Run workflow" button to start the process.

## Requirements

- Python 3.12.10
- Playwright

## License

This project is licensed under the MIT License.
