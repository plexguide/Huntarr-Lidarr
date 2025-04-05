#!/usr/bin/env python3
"""
Huntarr [Lidarr Edition] - Python Version
Main entry point for the application
"""

import time
import sys
import os
import json
from datetime import datetime, timedelta
from utils.logger import logger
from config import HUNT_MISSING_MODE, STATE_RESET_INTERVAL_HOURS, log_configuration
from missing.artist import process_artists_missing
from missing.album import process_albums_missing 
from upgrade.album import process_album_upgrades

# State file path
STATE_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")

def load_state():
    """Load the state file with processed items and last reset time"""
    if not os.path.exists(STATE_FILE_PATH):
        return {
            "processed_artists": [],
            "processed_albums": [],
            "last_reset_time": datetime.now().isoformat()
        }
    
    try:
        with open(STATE_FILE_PATH, 'r') as f:
            state = json.load(f)
            
            # Ensure last_reset_time exists
            if "last_reset_time" not in state:
                state["last_reset_time"] = datetime.now().isoformat()
                
            return state
    except Exception as e:
        logger.error(f"Error loading state file: {e}")
        return {
            "processed_artists": [],
            "processed_albums": [],
            "last_reset_time": datetime.now().isoformat()
        }

def save_state(state):
    """Save the state file with processed items and last reset time"""
    try:
        # Ensure last_reset_time is a string for JSON serialization
        if isinstance(state["last_reset_time"], datetime):
            state["last_reset_time"] = state["last_reset_time"].isoformat()
        
        with open(STATE_FILE_PATH, 'w') as f:
            json.dump(state, f)
    except Exception as e:
        logger.error(f"Error saving state file: {e}")

def check_reset_state(state):
    """Check if state reset interval has passed and reset if needed"""
    if STATE_RESET_INTERVAL_HOURS <= 0:
        # Never reset if interval is 0 or negative
        return state
        
    now = datetime.now()
    
    # Convert string to datetime if needed
    if isinstance(state["last_reset_time"], str):
        try:
            last_reset = datetime.fromisoformat(state["last_reset_time"])
        except ValueError:
            # If parsing fails, reset the time to now
            logger.warning("Invalid datetime format in state file. Resetting to now.")
            last_reset = now
    else:
        last_reset = state["last_reset_time"]
    
    reset_interval = timedelta(hours=STATE_RESET_INTERVAL_HOURS)
    
    if now - last_reset > reset_interval:
        logger.info(f"State reset interval ({STATE_RESET_INTERVAL_HOURS} hours) reached. Resetting processed items state.")
        state["processed_artists"] = []
        state["processed_albums"] = []
        state["last_reset_time"] = now
        
    return state

def main_loop() -> None:
    """Main processing loop for Huntarr-Lidarr"""
    while True:
        logger.info(f"=== Starting Huntarr-Lidarr cycle ===")
        
        # Load and check state
        state = load_state()
        state = check_reset_state(state)
        
        # Track if any processing was done in this cycle
        processing_done = False
        
        # 1) Handle missing content based on HUNT_MISSING_MODE
        if HUNT_MISSING_MODE in ["artist", "both"]:
            processed = process_artists_missing(state.get("processed_artists", []))
            if processed:
                state["processed_artists"] = processed
                processing_done = True
            
        if HUNT_MISSING_MODE in ["album", "both"]:
            processed = process_albums_missing(state.get("processed_albums", []))
            if processed:
                state["processed_albums"] = processed
                processing_done = True
            
        # 2) Handle album upgrade processing
        if process_album_upgrades():
            processing_done = True
            
        # Save updated state
        save_state(state)
        
        # Only wait if processing was actually done
        if processing_done:
            logger.info("Cycle complete. Waiting 60s before next cycle...")
            time.sleep(60)
            logger.info("⭐ Tool Great? Donate @ https://donate.plex.one for Daughter's College Fund!")
        else:
            # Shorter wait if nothing was processed
            logger.info("No processing performed. Waiting 10s before next cycle...")
            time.sleep(10)

if __name__ == "__main__":
    # Log configuration settings
    log_configuration(logger)

    try:
        main_loop()
    except KeyboardInterrupt:
        logger.info("Huntarr-Lidarr stopped by user.")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)