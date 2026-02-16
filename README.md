# Research Paper Info Extractor

A Python script that searches Google Scholar for open-access research papers, downloads them, and extracts evaluation metrics (accuracy, precision, recall, F1-score, etc.).

## Features

- 🔍 Searches Google Scholar for papers in any domain
- 📄 Finds open-access PDFs from multiple sources (Scholar [PDF] links, arXiv, direct PDFs)
- 📊 Extracts machine learning evaluation metrics:
  - Accuracy, Precision, Recall, F1-Score
  - AUC-ROC, Specificity, Sensitivity
  - MAE, MSE, RMSE
  - BLEU, ROUGE (for NLP papers)
- 📝 Saves results to a text file (Notepad format)
- 🔧 Handles errors gracefully (paywalls, invalid PDFs, citation entries)

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Install Required Packages

```bash
pip install requests beautifulsoup4 pdfplumber
```
Or install all at once:
```bash
pip install -r requirements.txt
```
Usage
Run the Script
```bash
python doc1.py
```
Follow the Prompts
Enter search topic: Type your research domain (e.g., "online exam proctoring computer vision")
Number of papers: How many open-access papers to find (default: 15)
Output filename: Name for the results file (default: scholar_results.txt)
Example
```plain
Enter search topic: behavioral biometrics exam proctoring
Number of papers to find [15]: 20
Save results to file [scholar_results.txt]: my_results.txt
```
Output
Text file: Contains paper titles, authors, years, and extracted metrics
PDF folder: Downloaded papers in open_access_papers/ directory
Sample Output
plain
Copy
================================================================================
PAPER #1
================================================================================

TITLE:
MANIT: a multilayer ANN integrated framework using biometrics...

AUTHORS:
M Malhotra, I Chhabra - Scientific Reports, 2025

YEAR: 2025
SOURCE: scholar_pdf

----------------------------------------
EVALUATION METRICS
----------------------------------------

  ACCURACY       : 0.9800 (98.00%)
  PRECISION      : 0.9700 (97.00%)
  RECALL         : 1.0000 (100.00%)
  F1 SCORE       : 0.9200 (92.00%)

  DATASETS USED: imagenet, coco
  MODELS: resnet, cnn, transformer
File Structure
```plain
research-paper-extractor/
├── doc1.py              # Main script
├── README.md            # This file
├── requirements.txt     # Python dependencies
├── scholar_results.txt  # Generated results (after running)
└── open_access_papers/  # Downloaded PDFs (created automatically)
```
Troubleshooting
"ModuleNotFoundError: No module named 'requests'"
Solution: Install required packages:
```bash
pip install requests beautifulsoup4 pdfplumber
```
"403 Client Error: Forbidden"
Cause: Some PDFs are behind paywalls or require authentication
Solution: The script automatically skips these and finds open-access alternatives
"[WinError 32] The process cannot access the file"
Cause: PDF file is locked by another program
Solution: Close any PDF readers and try again. The script will continue with other papers.
"TypeError: argument of type 'NoneType' is not iterable"
Cause: Bug in older versions when encountering citation entries
Solution: Use the latest version of the script (already fixed)
Notes
The script respects rate limits by adding delays between requests
Some papers may not have extractable metrics (shown as "No metrics found")
Results depend on open-access availability
For best results, search for CS/ML topics with many arXiv papers
License
This project is for educational and research purposes.
Author
Laam24