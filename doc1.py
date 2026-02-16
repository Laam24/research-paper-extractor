#!/usr/bin/env python3
"""
Google Scholar Open Access Paper Finder - Bug Fix Version
Fixed: TypeError when URL is None, citation entries
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import time
import re
from pathlib import Path
import sys
from datetime import datetime
import os


class OpenAccessFinder:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })
        self.download_dir = Path("open_access_papers")
        self.download_dir.mkdir(exist_ok=True)
        
        # Metric patterns
        self.metric_patterns = {
            'accuracy': [
                r'accuracy[:\s]+(\d+\.?\d*)\s*%',
                r'accuracy[:\s]+of\s+(\d+\.?\d*)',
                r'achieved\s+(?:an?\s+)?accuracy\s+(?:of\s+)?(\d+\.?\d*)',
                r'accuracy\s*[=:]\s*(\d+\.?\d*)',
                r'(\d+\.?\d*)%\s+accuracy',
            ],
            'precision': [
                r'precision[:\s]+(\d+\.?\d*)\s*%',
                r'precision[:\s]+of\s+(\d+\.?\d*)',
            ],
            'recall': [
                r'recall[:\s]+(\d+\.?\d*)\s*%',
                r'recall[:\s]+of\s+(\d+\.?\d*)',
            ],
            'f1_score': [
                r'f1[\s\-]?score[:\s]+(\d+\.?\d*)\s*%?',
                r'f1[:\s]+(\d+\.?\d*)\s*%',
            ],
            'auc_roc': [
                r'auc[\s\-]?roc[:\s]+(\d+\.?\d*)',
                r'auc\s*[=:]\s*(\d+\.?\d*)',
            ],
        }

    def find_papers(self, query, target_count=15):
        """Find open access papers."""
        papers = []
        page = 0
        max_pages = 50
        empty_pages = 0
        
        print(f"\n🔍 Searching: '{query}'")
        print(f"🎯 Target: {target_count} open access papers")
        print("-" * 70)
        
        while len(papers) < target_count and page < max_pages and empty_pages < 5:
            print(f"\n📄 Page {page + 1} ({len(papers)}/{target_count} found)")
            
            scholar_results = self._search_scholar_page(query, page)
            
            if not scholar_results:
                empty_pages += 1
                page += 1
                time.sleep(5)
                continue
            
            found_on_page = 0
            
            for paper_info in scholar_results:
                if len(papers) >= target_count:
                    break
                
                print(f"\n  Checking: {paper_info['title'][:50]}...")
                
                pdf_url = None
                pdf_source = None
                
                if paper_info.get('pdf_url'):
                    pdf_url = paper_info['pdf_url']
                    pdf_source = "scholar_pdf"
                    print(f"    ✅ Found [PDF] button link")
                
                # FIX: Check if title exists before calling _is_arxiv
                if not pdf_url and paper_info.get('title'):
                    if self._is_arxiv(paper_info):
                        print(f"    📝 Checking arXiv...")
                        arxiv_url = self._get_arxiv_pdf(paper_info['title'])
                        if arxiv_url:
                            pdf_url = arxiv_url
                            pdf_source = "arxiv"
                            print(f"    ✅ Found on arXiv")
                
                if not pdf_url and paper_info.get('url', '').endswith('.pdf'):
                    pdf_url = paper_info['url']
                    pdf_source = "direct_pdf"
                    print(f"    ✅ Direct PDF URL")
                
                if pdf_url:
                    pdf_path = self._download_pdf(pdf_url, paper_info['title'], pdf_source, len(papers))
                    
                    if pdf_path:
                        metrics = self._extract_comprehensive_metrics(pdf_path)
                        
                        papers.append({
                            **paper_info,
                            'source': pdf_source,
                            'pdf_path': str(pdf_path),
                            'pdf_url': pdf_url,
                            'metrics': metrics
                        })
                        
                        found_on_page += 1
                        print(f"    ✅ SUCCESS! Now have {len(papers)}/{target_count}")
                        
                        if metrics:
                            main_metrics = {k: v for k, v in metrics.items() 
                                          if k not in ['datasets', 'models_mentioned']}
                            if main_metrics:
                                print(f"       📊 Metrics: {main_metrics}")
                    else:
                        print(f"    ❌ Download failed")
                else:
                    print(f"    🔒 No open access version found")
                
                time.sleep(2)
            
            if found_on_page == 0:
                empty_pages += 1
            else:
                empty_pages = 0
            
            page += 1
            time.sleep(5)
        
        return papers

    def _search_scholar_page(self, query, page_num):
        """Search one page of Google Scholar."""
        start = page_num * 10
        url = f"https://scholar.google.com/scholar?q={quote_plus(query)}&start={start}&hl=en"
        
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = soup.select('.gs_r.gs_or.gs_scl')
            
            papers = []
            for result in results:
                try:
                    title_elem = result.select_one('.gs_rt')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True).replace('[PDF]', '').replace('[HTML]', '').strip()
                    
                    # FIX: Skip citation-only entries
                    if not title or title.startswith('[') or 'CITATION' in title or 'CITATION' in title_elem.get_text():
                        print(f"  ⚠️  Skipping citation entry")
                        continue
                    
                    authors_elem = result.select_one('.gs_a')
                    authors = authors_elem.get_text(strip=True) if authors_elem else 'Unknown'
                    year_match = re.search(r'\b(19|20)\d{2}\b', authors)
                    year = year_match.group(0) if year_match else 'N/A'
                    
                    link_elem = result.select_one('.gs_rt a')
                    main_url = link_elem['href'] if link_elem and link_elem.has_attr('href') else None
                    
                    pdf_url = None
                    pdf_elem = result.select_one('.gs_or_ggsm a[href]')
                    if pdf_elem:
                        pdf_url = pdf_elem['href']
                        if pdf_url.startswith('/'):
                            pdf_url = f"https://scholar.google.com{pdf_url}"
                    
                    papers.append({
                        'title': title,
                        'authors': authors,
                        'year': year,
                        'url': main_url,
                        'pdf_url': pdf_url,
                        'is_arxiv': 'arxiv.org' in (main_url or '') if main_url else False
                    })
                    
                except Exception as e:
                    continue
            
            return papers
            
        except Exception as e:
            print(f"  ❌ Scholar error: {e}")
            return []

    # FIX: Handle None values properly
    def _is_arxiv(self, paper_info):
        """Check if paper is from arXiv."""
        # FIX: Use or '' to default to empty string if None
        url = paper_info.get('url') or ''
        title = paper_info.get('title') or ''
        
        return 'arxiv.org' in url or bool(re.search(r'ar[xX]iv[.:]?\s*\d', title))

    def _get_arxiv_pdf(self, title):
        """Query arXiv API."""
        try:
            import xml.etree.ElementTree as ET
            search = re.sub(r'[^\w\s]', ' ', title)
            search = re.sub(r'\s+', ' ', search).strip()
            
            url = f"http://export.arxiv.org/api/query?search_query=all:{quote_plus(search)}&max_results=3"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                return None
            
            root = ET.fromstring(response.content)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            for entry in root.findall('.//atom:entry', ns):
                entry_title = entry.find('atom:title', ns)
                if entry_title is None:
                    continue
                
                et = entry_title.text.strip().lower()
                st = search.lower()
                
                if st in et or et in st or self._title_similarity(st, et) > 0.6:
                    for link in entry.findall('atom:link', ns):
                        if link.get('title') == 'pdf':
                            return link.get('href')
            
            return None
            
        except Exception as e:
            print(f"    ⚠️ arXiv error: {e}")
            return None

    def _title_similarity(self, s1, s2):
        """Calculate word overlap similarity."""
        words1 = set(s1.split())
        words2 = set(s2.split())
        if not words1 or not words2:
            return 0
        intersection = words1 & words2
        return len(intersection) / max(len(words1), len(words2))

    def _download_pdf(self, url, title, source, current_count):
        """Download PDF from URL."""
        try:
            clean = re.sub(r'[^\w\s-]', '', title)[:40].strip()
            filename = f"{source}_{current_count + 1}_{clean}.pdf"
            filepath = self.download_dir / filename
            
            if filepath.exists():
                return filepath
            
            print(f"    ⬇️  Downloading...")
            
            response = self.session.get(url, timeout=30, stream=True)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            with open(filepath, 'rb') as f:
                if f.read(4) != b'%PDF':
                    print(f"    ⚠️  Not a valid PDF")
                    filepath.unlink()
                    return None
            
            return filepath
            
        except Exception as e:
            print(f"    ❌ Download error: {e}")
            return None

    def _extract_comprehensive_metrics(self, pdf_path):
        """Extract comprehensive evaluation metrics from PDF."""
        metrics = {}
        
        try:
            text = self._extract_pdf_text_extended(pdf_path)
            
            if not text:
                return metrics
            
            text_lower = text.lower()
            
            for metric_name, patterns in self.metric_patterns.items():
                values_found = []
                
                for pattern in patterns:
                    matches = re.findall(pattern, text_lower, re.IGNORECASE)
                    for match in matches:
                        try:
                            if isinstance(match, tuple):
                                value = float(match[-1])
                            else:
                                value = float(match)
                            
                            if value > 1 and value <= 100:
                                value = value / 100
                            
                            values_found.append(value)
                        except:
                            continue
                
                if values_found:
                    if metric_name in ['mae', 'mse', 'rmse', 'perplexity']:
                        metrics[metric_name] = round(min(values_found), 4)
                    else:
                        metrics[metric_name] = round(max(values_found), 4)
            
            # Find datasets
            dataset_keywords = [
                'imagenet', 'coco', 'mnist', 'cifar-10', 'cifar-100', 'cifar10', 'cifar100',
                'squad', 'glue', 'wmt', 'pubmed', 'kitti', 'lfw', 'celeba', 'fer2013',
                'openimages', 'voc', 'pascal voc', 'cityscapes', 'ade20k'
            ]
            found_datasets = [d for d in dataset_keywords if d in text_lower]
            if found_datasets:
                metrics['datasets'] = found_datasets
            
            # Find models
            model_keywords = [
                'resnet', 'vgg', 'inception', 'mobilenet', 'efficientnet', 'yolo', 'faster r-cnn',
                'bert', 'gpt', 'transformer', 'lstm', 'gru', 'cnn', 'rnn', 'gan', 'vae',
                'densenet', 'alexnet', 'lenet', 'xception', 'nasnet'
            ]
            found_models = [m for m in model_keywords if m in text_lower]
            if found_models:
                metrics['models_mentioned'] = list(set(found_models))[:5]
            
            return metrics
            
        except Exception as e:
            print(f"    ⚠️  Extraction error: {e}")
            return metrics

    def _extract_pdf_text_extended(self, pdf_path):
        """Extract text from PDF."""
        text = ""
        
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages[:20]:
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    except:
                        continue
            return text
        except ImportError:
            pass
        
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(str(pdf_path))
            for page in reader.pages[:20]:
                try:
                    text += page.extract_text() + "\n"
                except:
                    continue
            return text
        except:
            pass
        
        return text


def save_to_notepad(papers, query, filename="scholar_results.txt"):
    """Save results to a text file formatted for Notepad."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            # Header
            f.write("=" * 80 + "\n")
            f.write("GOOGLE SCHOLAR OPEN ACCESS PAPER SEARCH RESULTS\n")
            f.write("=" * 80 + "\n\n")
            
            # Search info
            f.write(f"Search Query: {query}\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Papers Found: {len(papers)}\n")
            f.write("-" * 80 + "\n\n")
            
            if not papers:
                f.write("No open access papers were found for this query.\n")
                f.write("\nPossible reasons:\n")
                f.write("- Papers may be behind paywalls\n")
                f.write("- Try a more specific search query\n")
                f.write("- Try searching for CS/ML topics with many arXiv papers\n")
                return filename
            
            # Each paper
            for i, p in enumerate(papers, 1):
                f.write(f"\n{'=' * 80}\n")
                f.write(f"PAPER #{i}\n")
                f.write(f"{'=' * 80}\n\n")
                
                # Basic info
                f.write(f"TITLE:\n{p['title']}\n\n")
                f.write(f"AUTHORS:\n{p['authors']}\n\n")
                f.write(f"YEAR: {p['year']}\n")
                f.write(f"SOURCE: {p['source']}\n")
                f.write(f"PDF URL: {p['pdf_url']}\n")
                f.write(f"LOCAL PDF: {p['pdf_path']}\n\n")
                
                # Metrics section
                metrics = p.get('metrics', {})
                if metrics:
                    f.write("-" * 40 + "\n")
                    f.write("EVALUATION METRICS\n")
                    f.write("-" * 40 + "\n\n")
                    
                    standard_metrics = ['accuracy', 'precision', 'recall', 'f1_score', 'f1', 
                                      'auc_roc', 'auc', 'specificity', 'sensitivity', 
                                      'map', 'iou', 'mae', 'mse', 'rmse']
                    
                    found_any = False
                    for metric in standard_metrics:
                        if metric in metrics:
                            value = metrics[metric]
                            if value < 1:
                                display_value = f"{value:.4f} ({value*100:.2f}%)"
                            else:
                                display_value = f"{value:.4f}"
                            f.write(f"  {metric.upper().replace('_', ' '):<15}: {display_value}\n")
                            found_any = True
                    
                    if not found_any:
                        f.write("  No standard metrics found in paper.\n")
                    
                    if 'datasets' in metrics:
                        f.write(f"\n  DATASETS USED: {', '.join(metrics['datasets'])}\n")
                    
                    if 'models_mentioned' in metrics:
                        f.write(f"  MODELS: {', '.join(metrics['models_mentioned'])}\n")
                    
                    f.write("\n")
                else:
                    f.write("-" * 40 + "\n")
                    f.write("EVALUATION METRICS\n")
                    f.write("-" * 40 + "\n")
                    f.write("  No metrics could be extracted from this paper.\n\n")
            
            # Footer
            f.write("\n" + "=" * 80 + "\n")
            f.write("END OF REPORT\n")
            f.write("=" * 80 + "\n")
        
        print(f"\n💾 Results saved to Notepad file: {filename}")
        return filename
        
    except Exception as e:
        print(f"\n❌ Error saving to file: {e}")
        return None


def main():
    print("=" * 80)
    print("🔬 Google Scholar Open Access Paper Finder - Bug Fix Version")
    print("=" * 80)
    print("Fixed: TypeError when URL is None")
    print("-" * 80)
    
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        print("\n❌ Please install: pip install requests beautifulsoup4 pdfplumber")
        sys.exit(1)
    
    query = input("\nEnter search topic: ").strip()
    if not query:
        print("❌ Empty query")
        return
    
    try:
        num = int(input("Number of papers to find [15]: ") or "15")
    except:
        num = 15
    
    custom_name = input("Save results to file [scholar_results.txt]: ").strip()
    filename = custom_name if custom_name else "scholar_results.txt"
    
    finder = OpenAccessFinder()
    papers = finder.find_papers(query, num)
    
    print("\n" + "=" * 80)
    print(f"📚 SUMMARY: Found {len(papers)} open access papers")
    print("=" * 80)
    
    for i, p in enumerate(papers, 1):
        print(f"\n[{i}] {p['title'][:70]}...")
        metrics = p.get('metrics', {})
        if metrics:
            main_metrics = {k: v for k, v in metrics.items() 
                          if k not in ['datasets', 'models_mentioned']}
            if main_metrics:
                print(f"    Metrics: {main_metrics}")
    
    saved_file = save_to_notepad(papers, query, filename)
    
    if saved_file:
        print(f"\n✅ Complete! File saved: {saved_file}")
        print(f"📁 PDFs saved in: {finder.download_dir}/")
        
        try:
            os.startfile(saved_file)
            print(f"\n📋 Opening {saved_file} in Notepad...")
        except:
            pass


if __name__ == "__main__":
    main()