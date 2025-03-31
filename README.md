# PubMed Query Optimizer

This project is a tool to optimize complex PubMed search queries by automatically removing redundant OR keywords. It uses a combination of query parsing and Selenium automation to streamline searches and ensure the query returns the desired results.

## Overview

The tool:
- Parses a PubMed search query into its nested components.
- Identifies minimal operator groups (those containing AND/OR).
- Reconstructs the query by wrapping each keyword in parentheses.
- Uses Selenium to automate the PubMed search and verify result counts.
- Iteratively removes redundant keywords to optimize the query.

## Requirements

- Python 3.7+
- [Selenium](https://pypi.org/project/selenium/)
- [ChromeDriver](https://sites.google.com/chromium.org/driver/) (Ensure it is installed and available in your system's PATH)

## Installation

1. **Clone the Repository:**

    ```bash
    git clone https://github.com/yourusername/pubmed-query-optimizer.git
    cd pubmed-query-optimizer
    ```

2. **Create a Virtual Environment (Optional but Recommended):**

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3. **Install Dependencies:**

    ```bash
    pip install selenium
    ```

4. **Download ChromeDriver:**

    - Visit [ChromeDriver Downloads](https://sites.google.com/chromium.org/driver/) and download the version that matches your Chrome browser.
    - Make sure the `chromedriver` executable is in your PATH or in the project directory.

## Usage

Run the main script with your PubMed query as a command-line argument:

```bash
python main.py --query "YOUR_QUERY_HERE"
