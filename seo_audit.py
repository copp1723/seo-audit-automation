#!/usr/bin/env python3
"""
SEO Audit Automation Tool

This script automates the process of submitting URLs to SEOWORKS.AI,
capturing screenshots of the audit results, and organizing them into
a downloadable package.

Usage:
    python seo_audit.py --input urls.csv --output results.zip
"""

import os
import csv
import time
import logging
import argparse
import zipfile
from datetime import datetime
from urllib.parse import urlparse
from pathlib import Path

import pandas as pd
from tqdm import tqdm
from slugify import slugify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException


class SEOAuditAutomation:
    """Main class for SEO Audit automation."""

    def __init__(self, headless=True, log_level=logging.INFO):
        """
        Initialize the SEO Audit automation tool.

        Args:
            headless (bool): Whether to run browser in headless mode
            log_level: Logging level
        """
        self.driver = None
        self.headless = headless
        self.base_url = "https://seoworks.ai"
        self.email = "JOSH@PROJECTXLABS.AI"
        
        # Set up logging
        self.setup_logging(log_level)
        
    def setup_logging(self, log_level):
        """Set up logging configuration."""
        log_dir = Path(__file__).parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"seo_audit_{timestamp}.log"
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Logging initialized. Log file: {log_file}")

    def setup_driver(self):
        """Set up and configure the Selenium WebDriver."""
        self.logger.info("Setting up WebDriver...")
        
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        try:
            # Use the Homebrew-installed chromedriver
            service = Service(executable_path="/opt/homebrew/bin/chromedriver")
            self.logger.info("Using Homebrew-installed chromedriver")
                
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(60)
            self.logger.info("WebDriver setup complete")
        except WebDriverException as e:
            self.logger.error(f"Failed to set up WebDriver: {e}")
            raise

    def cleanup(self):
        """Clean up resources."""
        if self.driver:
            self.logger.info("Closing WebDriver...")
            self.driver.quit()
            self.driver = None

    def sanitize_filename(self, url):
        """
        Convert URL to a safe filename.
        
        Args:
            url (str): URL to convert
            
        Returns:
            str: Sanitized filename
        """
        parsed = urlparse(url)
        domain = parsed.netloc
        path = parsed.path.replace('/', '_')
        
        # Use slugify to create a safe filename
        filename = slugify(f"{domain}{path}")
        
        # Ensure filename is not too long
        if len(filename) > 100:
            filename = filename[:100]
            
        return filename

    def process_url(self, url, output_dir):
        """
        Process a single URL through SEOWORKS.AI.
        
        Args:
            url (str): URL to process
            output_dir (Path): Directory to save screenshot
            
        Returns:
            dict: Result information including status and screenshot path
        """
        result = {
            "url": url,
            "status": "failed",
            "screenshot_path": None,
            "error": None,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        try:
            self.logger.info(f"Processing URL: {url}")
            
            # Navigate to SEOWORKS.AI
            self.driver.get(self.base_url)
            self.logger.info("Navigated to SEOWORKS.AI")
            
            # Wait for page to load and take initial screenshot for debugging
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Take screenshot of initial page for debugging
            debug_screenshot = output_dir / f"debug_{self.sanitize_filename(url)}_initial.png"
            self.driver.save_screenshot(str(debug_screenshot))
            self.logger.info(f"Debug screenshot saved to {debug_screenshot}")
            
            # Find and fill URL input field - try multiple possible selectors
            url_input = None
            selectors = [
                "input[type='text']",
                "input[type='url']",
                "input[placeholder*='URL']",
                "input[placeholder*='url']",
                "input[placeholder*='website']",
                "input[name*='url']"
            ]
            
            for selector in selectors:
                try:
                    url_input = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if url_input.is_displayed():
                        break
                except (TimeoutException, NoSuchElementException):
                    continue
            
            if not url_input:
                self.logger.error(f"Could not find URL input field for {url}")
                result["error"] = "Could not find URL input field"
                return result
            
            url_input.clear()
            url_input.send_keys(url)
            self.logger.info(f"Entered URL: {url}")
            
            # Take screenshot after entering URL
            debug_screenshot = output_dir / f"debug_{self.sanitize_filename(url)}_url_entered.png"
            self.driver.save_screenshot(str(debug_screenshot))
            self.logger.info(f"Debug screenshot saved to {debug_screenshot}")
            
            # Submit URL - try multiple possible button selectors
            submit_button = None
            button_selectors = [
                "button[type='submit']",
                "//button[contains(text(), 'Analyze')]",
                "//button[contains(text(), 'Check')]",
                "//button[contains(text(), 'Audit')]",
                "//button[contains(text(), 'Submit')]",
                "input[type='submit']"
            ]
            
            for selector in button_selectors:
                try:
                    if selector.startswith("//"):
                        submit_button = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        submit_button = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    if submit_button.is_displayed():
                        break
                except (TimeoutException, NoSuchElementException):
                    continue
            
            if not submit_button:
                self.logger.error(f"Could not find submit button for {url}")
                result["error"] = "Could not find submit button"
                return result
            
            submit_button.click()
            self.logger.info("URL submitted")
            
            # Take screenshot after submission
            debug_screenshot = output_dir / f"debug_{self.sanitize_filename(url)}_submitted.png"
            self.driver.save_screenshot(str(debug_screenshot))
            self.logger.info(f"Debug screenshot saved to {debug_screenshot}")
            
            # Handle email input
            try:
                # Try multiple possible selectors for email input
                email_selectors = [
                    "input#email",
                    "input[type='email']",
                    "input[name='email']",
                    "input[placeholder*='email']",
                    "input[placeholder*='Email']",
                    "//input[@type='email']",
                    "//input[@name='email']"
                ]
                
                email_input = None
                for selector in email_selectors:
                    try:
                        if selector.startswith("//"):
                            email_input = WebDriverWait(self.driver, 3).until(
                                EC.presence_of_element_located((By.XPATH, selector))
                            )
                        else:
                            email_input = WebDriverWait(self.driver, 3).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                            )
                        if email_input.is_displayed():
                            break
                    except (TimeoutException, NoSuchElementException):
                        continue
                
                if not email_input:
                    self.logger.error(f"Could not find email input field for {url}")
                    result["error"] = "Could not find email input field"
                    return result
                
                email_input.clear()
                email_input.send_keys(self.email)
                self.logger.info(f"Entered email: {self.email}")
                
                # Take screenshot after entering email
                debug_screenshot = output_dir / f"debug_{self.sanitize_filename(url)}_email_entered.png"
                self.driver.save_screenshot(str(debug_screenshot))
                self.logger.info(f"Debug screenshot saved to {debug_screenshot}")
                
                # Try multiple possible selectors for final submit button
                final_submit_selectors = [
                    "//button[contains(text(), 'Submit')]",
                    "//button[contains(text(), 'Get Results')]",
                    "//button[contains(text(), 'Send')]",
                    "button[type='submit']",
                    "input[type='submit']"
                ]
                
                final_submit = None
                for selector in final_submit_selectors:
                    try:
                        if selector.startswith("//"):
                            final_submit = WebDriverWait(self.driver, 3).until(
                                EC.element_to_be_clickable((By.XPATH, selector))
                            )
                        else:
                            final_submit = WebDriverWait(self.driver, 3).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                            )
                        if final_submit.is_displayed():
                            break
                    except (TimeoutException, NoSuchElementException):
                        continue
                
                if not final_submit:
                    self.logger.error(f"Could not find final submit button for {url}")
                    result["error"] = "Could not find final submit button"
                    return result
                
                final_submit.click()
                self.logger.info("Email form submitted")
                
                # Take screenshot after final submission
                debug_screenshot = output_dir / f"debug_{self.sanitize_filename(url)}_final_submitted.png"
                self.driver.save_screenshot(str(debug_screenshot))
                self.logger.info(f"Debug screenshot saved to {debug_screenshot}")
                
            except Exception as e:
                self.logger.error(f"Failed to handle email form for {url}: {e}")
                result["error"] = f"Failed to handle email form: {str(e)}"
                return result
            
            # Wait for audit to complete and page to load
            self.logger.info("Waiting for audit to complete...")
            time.sleep(5)  # Initial wait
            
            # Wait for page to load after submission
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Handle popup if it appears
            try:
                popup_close = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, "//*[@id='cta_178493']/div/div[2]"))
                )
                popup_close.click()
                self.logger.info("Popup closed")
            except (TimeoutException, NoSuchElementException):
                self.logger.info("No popup detected or popup not clickable")
            
            # Take screenshot of audit results
            filename = self.sanitize_filename(url) + ".png"
            screenshot_path = output_dir / filename
            
            # Ensure we're capturing the full page
            self.logger.info("Taking screenshot of audit results...")
            
            # Get the height of the page
            height = self.driver.execute_script("return document.body.scrollHeight")
            
            # Set window size to capture full page
            self.driver.set_window_size(1920, height)
            
            # Take screenshot
            self.driver.save_screenshot(str(screenshot_path))
            self.logger.info(f"Screenshot saved to {screenshot_path}")
            
            result["status"] = "success"
            result["screenshot_path"] = str(screenshot_path)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Unexpected error processing {url}: {e}")
            result["error"] = f"Unexpected error: {str(e)}"
            return result

    def process_csv(self, csv_path, output_dir):
        """
        Process all URLs from a CSV file.
        
        Args:
            csv_path (str): Path to CSV file with URLs
            output_dir (str): Directory to save screenshots and results
            
        Returns:
            tuple: Lists of successful and failed URLs
        """
        output_path = Path(output_dir)
        screenshots_dir = output_path / "screenshots"
        screenshots_dir.mkdir(exist_ok=True, parents=True)
        
        results = []
        successful = []
        failed = []
        
        try:
            # Read URLs from CSV
            df = pd.read_csv(csv_path)
            
            # Check if CSV has at least one column
            if df.shape[1] == 0:
                self.logger.error("CSV file has no columns")
                raise ValueError("CSV file has no columns")
            
            # Get URLs from first column
            urls = df.iloc[:, 0].tolist()
            
            if not urls:
                self.logger.warning("No URLs found in the CSV file")
                return [], []
            
            self.logger.info(f"Found {len(urls)} URLs to process")
            
            # Set up WebDriver
            self.setup_driver()
            
            # Process each URL with progress bar
            for url in tqdm(urls, desc="Processing URLs"):
                result = self.process_url(url, screenshots_dir)
                results.append(result)
                
                if result["status"] == "success":
                    successful.append(url)
                else:
                    failed.append(url)
                
                # Add a small delay between requests to avoid rate limiting
                time.sleep(2)
            
            # Create results CSV
            results_df = pd.DataFrame(results)
            results_csv_path = output_path / "results.csv"
            results_df.to_csv(results_csv_path, index=False)
            self.logger.info(f"Results saved to {results_csv_path}")
            
            # Print summary
            self.logger.info(f"Total URLs processed: {len(urls)}")
            self.logger.info(f"Successful: {len(successful)} ({round(len(successful)/len(urls)*100 if urls else 0, 1)}%)")
            self.logger.info(f"Failed: {len(failed)} ({round(len(failed)/len(urls)*100 if urls else 0, 1)}%)")
            
            return successful, failed
            
        except Exception as e:
            self.logger.error(f"Error processing CSV: {e}")
            raise
        finally:
            self.cleanup()

    def create_zip(self, output_dir, zip_path=None):
        """
        Create a ZIP file with all results.
        
        Args:
            output_dir (str): Directory with results
            zip_path (str, optional): Path for ZIP file
            
        Returns:
            str: Path to created ZIP file
        """
        output_path = Path(output_dir)
        
        if zip_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_path = output_path.parent / f"seo_audit_results_{timestamp}.zip"
        else:
            zip_path = Path(zip_path)
        
        self.logger.info(f"Creating ZIP file: {zip_path}")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add all files in output directory to ZIP
            for root, _, files in os.walk(output_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, output_path.parent)
                    zipf.write(file_path, arcname)
        
        self.logger.info(f"ZIP file created: {zip_path}")
        return str(zip_path)


def main():
    """Main function to run the SEO audit automation."""
    parser = argparse.ArgumentParser(description="SEO Audit Automation Tool")
    parser.add_argument("--input", required=True, help="Path to CSV file with URLs")
    parser.add_argument("--output", default=None, help="Path for output ZIP file")
    parser.add_argument("--visible", action="store_true", help="Run browser in visible mode")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Set up output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(__file__).parent.parent / "output" / f"run_{timestamp}"
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # Set log level
    log_level = logging.DEBUG if args.debug else logging.INFO
    
    # Initialize automation
    automation = SEOAuditAutomation(headless=not args.visible, log_level=log_level)
    
    try:
        # Process URLs
        successful, failed = automation.process_csv(args.input, output_dir)
        
        # Create ZIP file
        zip_path = automation.create_zip(output_dir, args.output)
        
        # Print summary
        print("\n==========================================================")
        print("SEO Audit Automation Complete!")
        print("==========================================================")
        print(f"Total URLs processed: {len(successful) + len(failed)}")
        print(f"Successful: {len(successful)}")
        print(f"Failed: {len(failed)}")
        print(f"Results saved to: {zip_path}")
        print("==========================================================")
        
    except KeyboardInterrupt:
        print("\nProcess interrupted. Cleaning up...")
        logging.warning("Process interrupted by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
        logging.error(f"Error in main: {e}", exc_info=True)


if __name__ == "__main__":
    main()
