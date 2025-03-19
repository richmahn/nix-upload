import os
import random
import time
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import traceback
import re
import logging
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

def save_debug_snapshot(driver, label):
    """Save screenshot and page source for debugging."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_label = label.replace(" ", "_").lower()
    os.makedirs("debug", exist_ok=True)
    
    screenshot_path = os.path.join("debug", f"{timestamp}_{safe_label}.png")
    html_path = os.path.join("debug", f"{timestamp}_{safe_label}.html")
    
    try:
        driver.save_screenshot(screenshot_path)
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        logger.debug(f"Saved debug snapshot: {screenshot_path}, {html_path}")
    except Exception as e:
        logger.error(f"Failed to save debug snapshot for '{label}': {e}")


def load_config(config_file='config.json'):
    """Load configuration from JSON file."""
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        required_keys = ['username', 'password', 'playlist_name', 'photos_directory', 'max_photos', 'base_url']
        for key in required_keys:
            if key not in config:
                raise KeyError(f"Missing required key '{key}' in config file")
        
        return config
    except FileNotFoundError:
        logger.error(f"Config file '{config_file}' not found.")
        exit(1)
    except json.JSONDecodeError:
        logger.error(f"Failure parsing config file '{config_file}'. Please ensure it's valid JSON.")
        exit(1)
    except Exception as e:
        logger.error(f"Failure loading config: {str(e)}")
        exit(1)


import os

import os

def get_image_files(directory, max_file_size_mb, max_photos):
    """Recursively get all image files from a directory, skipping folders with a .nonixplay file."""
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
    image_files = []

    try:
        for root, dirs, files in os.walk(directory):
            # Skip this directory if it contains a .nonixplay file
            if '.nonixplay' in files:
                logger.debug(f"Skipping directory: {root} (contains .nonixplay)")
                dirs[:] = []  # Prevent descending into subdirectories
                continue

            for file in files:
                if any(file.lower().endswith(ext) for ext in valid_extensions):
                    image_files.append(os.path.join(root, file))

        max_file_size = max_file_size_mb * 1024 * 1024
        # Filter out large files
        filtered_images = [f for f in image_files if os.path.getsize(f) <= max_file_size]
        logger.debug(f"Filtered images: {len(filtered_images)} files below the {max_file_size_mb}MB limit.")
        
        # Randomly select max_photos number of photos
        import random
        if len(filtered_images) > max_photos:
            selected_images = random.sample(filtered_images, max_photos)
            logger.info(f"Randomly selected {len(selected_images)} photos for upload.")
        else:
            selected_images = filtered_images
            logger.info(f"Selected all {len(selected_images)} photos for upload (fewer than max_photos).")

        return selected_images        
    except FileNotFoundError:
        logger.error(f"Directory '{directory}' not found.")
        exit(1)
    except Exception as e:
        logger.error(f"get_image_files() Exception: {str(e)}")
        exit(1)


def setup_webdriver():
    """Set up and configure Chrome WebDriver."""
    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--ignore-certificate-errors")
        options.page_load_strategy = 'normal'
        
        # by defdault we want headless
        options.headless = True
        options.add_argument("--headless")
        
        options.add_argument("--log-level=1") # cap the loglevel at INFO
        
        # gemini
        options.add_argument("--silent")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(60)
        return driver
    except Exception as e:
        logger.error(f"Failed setting up WebDriver: {str(e)}")
        exit(1)


def login_to_nixplay(driver, base_url, username, password):
    """Log in to Nixplay account."""
    try:
        logger.debug("Logging in to Nixplay...")
        login_url = f"{base_url}/login"
        driver.get(login_url)
        save_debug_snapshot(driver, "login_page_loaded")
        
        wait = WebDriverWait(driver, 40)

        logger.debug("Waiting for email field...")
        email_field = wait.until(EC.presence_of_element_located((By.ID, "login_username")))
        logger.debug("Found email field.")
        
        logger.debug("Waiting for password field...")
        password_field = wait.until(EC.presence_of_element_located((By.ID, "login_password")))
        logger.debug("Found password field.")
        
        email_field.send_keys(username)
        password_field.send_keys(password)
        
        logger.debug("Looking for login button...")
        login_button = wait.until(EC.element_to_be_clickable((By.ID, "nixplay_login_btn")))
        logger.debug("Clicking login button...")
        login_button.click()
        
        # Wait until the login redirects (e.g., away from /login)
        wait.until(EC.url_changes(login_url))
        
        logger.info("Successfully logged in to nixplay.")
        save_debug_snapshot(driver, "login_successful")
        return True
    except TimeoutException:
        logger.error("Timeout while trying to log in.")
        save_debug_snapshot(driver, "login_failed_timeout")
        return False
    except Exception as e:
        logger.error(f"Failed to login: {str(e)}")
        save_debug_snapshot(driver, "login_failed_exception")
        return False

def find_playlist(driver, base_url, playlist_name):
    """Find and select the specified playlist by name, then index."""
    try:
        logger.debug(f"Finding playlist: {playlist_name}...")
        playlists_url = f"{base_url}/#/playlists"
        driver.get(playlists_url)

        wait = WebDriverWait(driver, 30)

        # Find the playlist's name element.
        playlist_name_element = wait.until(
            EC.presence_of_element_located((By.XPATH, f'//span[@class="name" and @title="{playlist_name}"]'))
        )

        # Find the parent playlist container and extract the index from the ID.
        playlist_container = playlist_name_element.find_element(By.XPATH, "./ancestor::div[contains(@id, 'playlist-')]")
        playlist_id = playlist_container.get_attribute("id")
        playlist_index = int(re.search(r'\d+', playlist_id).group()) #extract the digits

        logger.info(f"Found playlist '{playlist_name}' with index: {playlist_index}")

        # Find the playlist's clickable element using the index.
        playlist_element = wait.until(
            EC.element_to_be_clickable((By.XPATH, f'//div[@id="playlist-{playlist_index}"]//div[@class="playlist-draggable-wrapper"]'))
        )

        playlist_element.click()

        wait.until(EC.url_contains("/playlist/"))
        save_debug_snapshot(driver, f"playlist_selected_{playlist_name}")
        return True

    except Exception as e:
        logger.error(f"Could not find playlist: {repr(e)}")
        traceback.print_exc()
        save_debug_snapshot(driver, "find_playlist_error")
        return False



# import time
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC

def delete_all_photos(driver, timeout=10):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException
    import time

    try:
        logger.debug("Switching to main document...")
        driver.switch_to.default_content()
        wait = WebDriverWait(driver, timeout)


        # Step 2: Open Actions dropdown
        logger.debug("Locating and clicking Actions button...")
        actions_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'dropdown-toggle') and contains(@class, 'btn-gray')]"))
        )
        actions_button.click()
        logger.debug("Clicked Actions button.")
        save_debug_snapshot(driver, "after_actions_clicked")

        # Step 3: Click "Permanent delete all photos"
        logger.debug("Clicking 'Permanent delete all photos'...")
        delete_all_perm = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(@ng-click, 'deleteAllSlides') and contains(@ng-click, 'delete')]"))
        )
        delete_all_perm.click()
        logger.debug("Clicked 'Permanent delete all photos'.")
        save_debug_snapshot(driver, "after_delete_all_clicked")

        # Step 4: Wait for modal and read title
        logger.debug("Waiting for modal to appear...")
        modal_title_elem = wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".nix-modal-title-text"))
        )
        modal_text = modal_title_elem.text.strip()
        logger.debug(f"Modal title detected: '{modal_text}'")
        save_debug_snapshot(driver, "modal_detected")

        if modal_text == "No Photo in Playlist":
            logger.debug("'No Photo in Playlist' modal detected.")
            ok_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='OK']")))
            save_debug_snapshot(driver, "before_clicking_ok")
            ok_button.click()
            logger.info("Clicked 'OK' on No Photo modal.")
            return True
        else:
            logger.debug("Confirmation modal detected (not 'No Photo'). Proceeding to click 'Yes'.")
            save_debug_snapshot(driver, "before_clicking_yes")
            yes_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Yes']")))
            yes_button.click()
            logger.info("Clicked 'Yes' to confirm deletion.")
            return True

    except TimeoutException as e:
        logger.error(f"delete_all_photos() TimeoutException: {str(e)}")
        save_debug_snapshot(driver, "timeout_exception")
        return False

    except Exception as e:
        logger.error(f"delete_all_photos() Exception: {str(e)}")
        save_debug_snapshot(driver, "unexpected_exception")
        return False

      

       

class invisibility_of_any_element:
    def __init__(self, locators):
        self.locators = locators

    def __call__(self, driver):
        return all(EC.invisibility_of_element_located(locator)(driver) for locator in self.locators)

import json


import os
import time
import random
import traceback
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementClickInterceptedException

def upload_batch(driver, batch, batch_number, batch_count, batch_end_count, logfile):
    logger.debug(f"batch_number={batch_number}, batch_end_count={batch_end_count}")
    
    """Upload a single batch of photos and monitor progress."""
    wait = WebDriverWait(driver, 120)
    
    # Display all file names in this batch
    logger.debug(f"Files in this batch:")
    for idx, file_path in enumerate(batch):
        logger.debug(f"  {idx+1}. {os.path.basename(file_path)}")
    
    
    
    # Click "Add photos"
    try:
        wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, ".nix-upload-modal-bg")))
        add_photos_button = wait.until(EC.element_to_be_clickable((By.ID, "add-photos")))
        driver.execute_script("arguments[0].scrollIntoView(true);", add_photos_button)
        driver.execute_script("arguments[0].click();", add_photos_button)
    except Exception as e:
        logger.warning(f"❌ Error clicking 'Add photos': {e}, continuing")
        save_debug_snapshot(driver, f"add_photos_error_batch_{batch_number}")
        return False
        
    # Click "From my computer"
    try:
        from_computer = wait.until(EC.presence_of_element_located((By.XPATH, "//span[text()='From my computer']")))
        driver.execute_script("arguments[0].click();", from_computer)
    except Exception as e:
        logger.warning(f"❌ Error clicking 'From my computer': {e}, continuing")
        save_debug_snapshot(driver, f"from_my_computer_error_batch_{batch_number}")
        return False
        
    # Upload files
    try:
        file_input = wait.until(EC.presence_of_element_located((By.ID, "upload")))
        # Debug print: List of files to be sent
        files_to_send = "\n".join([os.path.abspath(f) for f in batch])
        logger.debug("Debug: Files being sent to input field:\n" + files_to_send)
        file_input.send_keys(files_to_send)
        try:
            logfile.write(files_to_send)
        except Exception as e:
            logger.warning(f"Error writing log of files: {e}, continuing")
            
    except Exception as e:
        logger.warning(f"Error sending files to input: {e}, continuing")
        save_debug_snapshot(driver, f"upload_input_error_batch_{batch_number}")
        return False
        
        
    # Monitor upload progress
    logger.debug("Waiting for upload progress indicator...")
    upload_text_xpath = "//span[contains(text(), 'files completed')]"
    try:
        wait.until(EC.presence_of_element_located((By.XPATH, upload_text_xpath)))
    except TimeoutException:
        logger.warning("⚠️ Upload progress text not found. Continuing")
        save_debug_snapshot(driver, f"upload_progress_not_found_batch_{batch_number}")
        return False
    
    logger.debug("Monitoring batch upload progress...")
    last_progress = 0
    last_progress_change_time = time.time()
    stall_timeout = max(200, len(batch))  # batch_size seconds to wait if progress stops changing
    max_upload_time = max(300, 2 * len(batch))  # maximum 2*batch_size seconds per batch
    start_time = time.time()

    while True:
        # Check for absolute timeout
        if time.time() - start_time > max_upload_time:
            logger.info(f"\nMaximum upload time ({max_upload_time}s) reached. Assuming complete.")
            break
            
        time.sleep(2)
        try:
            upload_text_elem = driver.find_element(By.XPATH, upload_text_xpath)
            text = upload_text_elem.text.strip()
            
            # Try to parse progress
            current_progress = 0
            try:
                if " of " in text:
                    parts = text.split(" of ")
                    current_progress = int(parts[0])
                    # Get the total from the text which may be different from our batch size
                    website_total = int(parts[1].split(" ")[0])
            except ValueError:
                logger.warning("Progress bar {text} could not be parsed. Continuing")
                pass  # Progress couldn't be parsed
                
            if current_progress > 0:
                # Calculate the progress relative to this batch
                total_for_batch = len(batch)
                    
                batch_start_count = (batch_number-1)*total_for_batch+1
                batch_progress = current_progress - batch_start_count + 1
                
                # Make sure batch_progress doesn't go negative (shouldn't happen but just in case)
                batch_progress = max(0, batch_progress)
                # Dot-based progress bar for this batch
                bar_width = 20
                progress_ratio = min(batch_progress / total_for_batch, 1.0)
                dots = int(progress_ratio * bar_width)
                spaces = bar_width - dots
                progress_bar = "." * dots + " " * spaces
                
                print(f"\rUploading: [{progress_bar}] {batch_progress}/{total_for_batch} (Total: {current_progress}/{website_total}) (Batch {batch_number} of {batch_count})", end="")
                
                # Check if progress changed
                if current_progress != last_progress:
                    last_progress = current_progress
                    last_progress_change_time = time.time()
                    
                # If we reached the expected end count for this batch, exit
                if current_progress >= batch_end_count:
                    time.sleep(5)  # Give it 5 seconds after reaching target
                    logger.debug(f"\nUpload reached target {batch_end_count} - batch complete")
                    break
            else:
                print(f"\rUploading: Waiting for progress update... ('{text}')", end="")
                
            # Check for stalled progress
            if time.time() - last_progress_change_time > stall_timeout:
                logger.info(f"\nProgress stalled for {stall_timeout}s - assuming upload complete")
                break
                
        except NoSuchElementException:
            # Progress element has disappeared
            logger.info("\nUpload complete - progress indicator disappeared. Continuing")
            break
        except Exception as e:
            logger.warning(f"\nWarning reading progress: {e}. Continuing")
            # Don't update the last_progress_change_time on errors
    
    print(f"\r")
    logger.debug(f"Batch {batch_number} upload complete.")
    return True


def upload_photos(driver, selected_images, batch_size):
    """Upload photos to the current playlist in batches."""
    try:
        # logger.info("Preparing to upload photos max_file_size_mb=%d, max_photos=%d, batch_size=%d ..." % (max_file_size_mb, max_photos, batch_size))
        
        # Track cumulative uploads across all batches
        cumulative_uploaded_count = 0

        # Write cumulative list to debug file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        debug_file_name = f"{timestamp}_uploaded_files.txt"
        logfile=None
        try:
            # os.makedirs("debug", exist_ok=True)
            debug_file_path = os.path.join("debug", debug_file_name)  # Use debug_screenshots directory
            logfile=open(debug_file_path, "w")
        except Exception as e:
            logger.warning(f"Error creating {debug_file_name}. Continuing")
           
       
        for i in range(0, len(selected_images), batch_size):
            batch = selected_images[i:i + batch_size]
            batch_number = i // batch_size + 1
            batch_count = ((len(selected_images) - 1) // batch_size + 1)

            # Expected start and end counts for this batch
            batch_end_count = cumulative_uploaded_count + len(batch)

            
            # Upload the batch
            logger.debug(f"Uploading batch {batch_number} of {batch_count} ({len(batch)} photos)...")
            batch_success = upload_batch(
                driver, 
                batch, 
                batch_number, 
                batch_count,
                batch_end_count,
                logfile
            )
            
            if batch_success:
                # Update the cumulative count for the next batch
                cumulative_uploaded_count += len(batch)

            
            # Optional: wait briefly between batches
            time.sleep(5)
            
        logger.info("All batches uploaded.")
        
        logger.info(f"List of all uploaded files written to {debug_file_path}")
        return True
        
    except Exception as e:
        logger.error(f"upload_photos() Exception: {e}")
        save_debug_snapshot(driver, "upload_exception")
        return False
        
def main():
    """Main function to orchestrate the Nixplay photo upload process."""
    config = load_config()
    username = config['username']
    password = config['password']
    playlist_name = config['playlist_name']
    photos_directory = config['photos_directory']
    max_photos = config['max_photos']
    base_url = config['base_url'].rstrip('/')
    max_file_size_mb = config['max_file_size_mb']
    batch_size = config['batch_size']
    
    image_files = get_image_files(photos_directory, max_file_size_mb, max_photos)
    if not image_files:
        logger.error(f"No image files found in '{photos_directory}'.")
        exit(1)
    logger.info(f"Found {len(image_files)} image files.")
    
    driver = setup_webdriver()
    
    try:
        if not login_to_nixplay(driver, base_url, username, password):
            logger.error("Login failed. Exiting.")
            exit(1)
        
        if not find_playlist(driver, base_url, playlist_name):
            logger.error(f"Could not find playlist '{playlist_name}'. Exiting.")
            exit(1)
        
        if not delete_all_photos(driver):
            logger.error("Failed to delete existing photos. Continuing with upload...")
        
        if not upload_photos(driver, image_files, batch_size):
            logger.error("Failed to upload photos.")
            exit(1)
        
        logger.info("Nixplay photo upload completed successfully!")
    except Exception as e:
        logger.error(f"main() Exception: {str(e)}")
        save_debug_snapshot(driver, "unexpected_error")
    finally:
        logger.debug("Closing WebDriver...")
        save_debug_snapshot(driver, "final_state_before_exit")
        driver.quit()


if __name__ == "__main__":
    main()
