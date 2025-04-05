#!/usr/bin/env python3
"""
Huntarr [Lidarr Edition] - Python Version
Main entry point for the application
"""

import os
import time
import json
import random
import logging
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

# ---------------------------
# Environment Variables
# ---------------------------

API_KEY = os.environ.get("API_KEY", "your-api-key")
API_URL = os.environ.get("API_URL", "http://your-lidarr-address:8686")

# Missing Content Settings
try:
    HUNT_MISSING_ITEMS = int(os.environ.get("HUNT_MISSING_ITEMS", "1"))
except ValueError:
    HUNT_MISSING_ITEMS = 1
    print(f"[WARN] Invalid HUNT_MISSING_ITEMS value; using default {HUNT_MISSING_ITEMS}")

# Upgrade Settings
try:
    HUNT_UPGRADE_ALBUMS = int(os.environ.get("HUNT_UPGRADE_ALBUMS", "0"))
except ValueError:
    HUNT_UPGRADE_ALBUMS = 0
    print(f"[WARN] Invalid HUNT_UPGRADE_ALBUMS value; using default {HUNT_UPGRADE_ALBUMS}")

# Sleep duration in seconds after completing each item (default 900 = 15 minutes)
try:
    SLEEP_DURATION = int(os.environ.get("SLEEP_DURATION", "900"))
except ValueError:
    SLEEP_DURATION = 900
    print(f"[WARN] Invalid SLEEP_DURATION value; using default {SLEEP_DURATION}")

# If True, pick items randomly; if False, go in order
RANDOM_SELECTION = os.environ.get("RANDOM_SELECTION", "true").lower() == "true"

# If MONITORED_ONLY=true, only process monitored artists/albums/tracks
MONITORED_ONLY = os.environ.get("MONITORED_ONLY", "true").lower() == "true"

# HUNT_MISSING_MODE: "artist", "album", or "both"
HUNT_MISSING_MODE = os.environ.get("HUNT_MISSING_MODE", "artist")

# State Reset Interval (in hours) - This resets the processed items state
# Set to 0 to never reset (always remember processed items)
try:
    STATE_RESET_INTERVAL_HOURS = int(os.environ.get("STATE_RESET_INTERVAL_HOURS", "168"))
except ValueError:
    STATE_RESET_INTERVAL_HOURS = 168  # Default to 1 week
    print(f"[WARN] Invalid STATE_RESET_INTERVAL_HOURS value; using default {STATE_RESET_INTERVAL_HOURS}")

# Enable debug logging
DEBUG_MODE = os.environ.get("DEBUG_MODE", "false").lower() == "true"

logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("huntarr-lidarr")

# State file path
STATE_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")

# ---------------------------
# Lidarr API Helper Functions
# ---------------------------

def lidarr_request(endpoint: str, method: str = "GET", data: Dict = None, params: Dict = None) -> Optional[Any]:
    """
    Perform a request to the Lidarr API (v1).
    Example endpoint: "artist", "album", "track", "command", or "qualityprofile".
    """
    url = f"{API_URL}/api/v1/{endpoint}"
    headers = {
        "X-Api-Key": API_KEY,
        "Content-Type": "application/json",
    }
    try:
        if method.upper() == "GET":
            resp = requests.get(url, headers=headers, params=params, timeout=30)
        else:  # Typically "POST"
            resp = requests.post(url, headers=headers, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.error(f"API request error to {url}: {e}")
        return None

def get_artists_json() -> Optional[List[Dict]]:
    return lidarr_request("artist", "GET")

def get_albums_for_artist(artist_id: int) -> Optional[List[Dict]]:
    return lidarr_request(f"album?artistId={artist_id}", "GET")

def get_tracks_for_album(album_id: int) -> Optional[List[Dict]]:
    return lidarr_request(f"track?albumId={album_id}", "GET")

def get_quality_profiles() -> Dict[int, Dict]:
    """
    Returns a dict like:
      { profileId: { 'id': <id>, 'name': <str>, 'cutoff': <int>, 'items': [ ... ] }, ... }
    
    'cutoff' is typically an integer ID representing the minimum acceptable quality.
    """
    resp = lidarr_request("qualityprofile", "GET")
    if not resp or not isinstance(resp, list):
        logger.warning("Could not retrieve quality profiles or invalid format.")
        return {}
    profiles = {}
    for p in resp:
        prof_id = p.get("id")
        if prof_id is not None:
            profiles[prof_id] = p
    return profiles

def refresh_artist(artist_id: int) -> Optional[Dict]:
    """
    POST /api/v1/command
    { "name": "RefreshArtist", "artistIds": [ artist_id ] }
    """
    data = {
        "name": "RefreshArtist",
        "artistIds": [artist_id],
    }
    return lidarr_request("command", method="POST", data=data)

def missing_album_search(artist_id: int) -> Optional[Dict]:
    """
    POST /api/v1/command
    { "name": "MissingAlbumSearch", "artistIds": [ artist_id ] }
    """
    data = {
        "name": "MissingAlbumSearch",
        "artistIds": [artist_id],
    }
    return lidarr_request("command", method="POST", data=data)

def album_search(album_id: int) -> Optional[Dict]:
    """
    POST /api/v1/command
    { "name": "AlbumSearch", "albumIds": [ album_id ] }
    """
    data = {
        "name": "AlbumSearch",
        "albumIds": [album_id],
    }
    return lidarr_request("command", method="POST", data=data)

def track_search(track_id: int) -> Optional[Dict]:
    """
    POST /api/v1/command
    { "name": "TrackSearch", "trackIds": [ track_id ] }
    """
    data = {
        "name": "TrackSearch",
        "trackIds": [track_id],
    }
    return lidarr_request("command", method="POST", data=data)

# ---------------------------
# State Management Functions
# ---------------------------

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

# ---------------------------
# MISSING: ARTIST MODE
# ---------------------------
def process_artists_missing(processed_artists=None) -> List[int]:
    """Process artists with missing tracks"""
    logger.info("=== Running in ARTIST MODE (Missing) ===")
    
    if processed_artists is None:
        processed_artists = []
    
    # Skip if HUNT_MISSING_ITEMS is set to 0
    if HUNT_MISSING_ITEMS <= 0:
        logger.info("HUNT_MISSING_ITEMS is set to 0, skipping artist missing content")
        return processed_artists
        
    artists = get_artists_json()
    if not artists:
        logger.error("ERROR: Unable to retrieve artist data. Retrying in 60s...")
        time.sleep(60)
        logger.info("⭐ Tool Great? Donate @ https://donate.plex.one for Daughter's College Fund!")
        return processed_artists

    # Filter for artists with missing tracks
    if MONITORED_ONLY:
        logger.info("MONITORED_ONLY=true => only monitored artists with missing tracks.")
        incomplete_artists = [
            a for a in artists
            if a.get("monitored") is True
            and a.get("statistics", {}).get("trackCount", 0) > a.get("statistics", {}).get("trackFileCount", 0)
            and a.get("id") not in processed_artists
        ]
    else:
        logger.info("MONITORED_ONLY=false => all incomplete artists.")
        incomplete_artists = [
            a for a in artists
            if a.get("statistics", {}).get("trackCount", 0) > a.get("statistics", {}).get("trackFileCount", 0)
            and a.get("id") not in processed_artists
        ]

    if not incomplete_artists:
        if not processed_artists:
            logger.info("No incomplete artists found.")
        else:
            logger.info("All incomplete artists already processed.")
        return processed_artists

    logger.info(f"Found {len(incomplete_artists)} incomplete artist(s).")
    logger.info(f"Processing up to {HUNT_MISSING_ITEMS} artists this cycle.")
    
    processed_count = 0
    used_indices = set()
    newly_processed = []

    # Process artists up to HUNT_MISSING_ITEMS
    while True:
        if processed_count >= HUNT_MISSING_ITEMS:
            logger.info(f"Reached HUNT_MISSING_ITEMS ({HUNT_MISSING_ITEMS}). Exiting loop.")
            break
        if len(used_indices) >= len(incomplete_artists):
            logger.info("All incomplete artists processed. Exiting loop.")
            break

        # Select next artist (randomly or sequentially)
        if RANDOM_SELECTION and len(incomplete_artists) > 1:
            while True:
                idx = random.randint(0, len(incomplete_artists) - 1)
                if idx not in used_indices:
                    break
        else:
            idx_candidates = [i for i in range(len(incomplete_artists)) if i not in used_indices]
            if not idx_candidates:
                break
            idx = idx_candidates[0]

        used_indices.add(idx)
        artist = incomplete_artists[idx]
        artist_id = artist["id"]
        artist_name = artist.get("artistName", "Unknown Artist")
        track_count = artist.get("statistics", {}).get("trackCount", 0)
        track_file_count = artist.get("statistics", {}).get("trackFileCount", 0)
        missing = track_count - track_file_count

        logger.info(f"Processing artist: '{artist_name}' (ID={artist_id}), missing {missing} track(s).")

        # 1) Refresh artist
        refresh_resp = refresh_artist(artist_id)
        if not refresh_resp or "id" not in refresh_resp:
            logger.warning("WARNING: Could not refresh. Skipping this artist.")
            time.sleep(10)
            logger.info("⭐ Tool Great? Donate @ https://donate.plex.one for Daughter's College Fund!")
            continue
        logger.info(f"Refresh command accepted (ID={refresh_resp['id']}). Waiting 5s...")
        time.sleep(5)

        # 2) MissingAlbumSearch
        search_resp = missing_album_search(artist_id)
        if search_resp and "id" in search_resp:
            logger.info(f"MissingAlbumSearch accepted (ID={search_resp['id']}).")
            # Add to processed list
            newly_processed.append(artist_id)
        else:
            logger.warning("WARNING: MissingAlbumSearch failed. Trying fallback 'AlbumSearch' by artist...")
            fallback_data = {
                "name": "AlbumSearch",
                "artistIds": [artist_id],
            }
            fallback_resp = lidarr_request("command", method="POST", data=fallback_data)
            if fallback_resp and "id" in fallback_resp:
                logger.info(f"Fallback AlbumSearch accepted (ID={fallback_resp['id']}).")
                # Add to processed list
                newly_processed.append(artist_id)
            else:
                logger.warning("Fallback also failed. Skipping this artist.")

        processed_count += 1
        logger.info(f"Processed artist.")
    
    # Return updated processed list
    return processed_artists + newly_processed

# ---------------------------
# MISSING: ALBUM MODE
# ---------------------------
def process_albums_missing(processed_albums=None) -> List[int]:
    """Process albums with missing tracks"""
    logger.info("=== Running in ALBUM MODE (Missing) ===")
    
    if processed_albums is None:
        processed_albums = []
    
    # Skip if HUNT_MISSING_ITEMS is set to 0
    if HUNT_MISSING_ITEMS <= 0:
        logger.info("HUNT_MISSING_ITEMS is set to 0, skipping album missing content")
        return processed_albums
        
    artists = get_artists_json()
    if not artists:
        logger.error("ERROR: No artist data.")
        return processed_albums

    incomplete_albums = []

    # Gather all incomplete albums from all artists
    for artist in artists:
        artist_id = artist["id"]
        artist_name = artist.get("artistName", "Unknown Artist")
        artist_monitored = artist.get("monitored", False)

        if MONITORED_ONLY and not artist_monitored:
            continue

        albums = get_albums_for_artist(artist_id) or []
        for alb in albums:
            album_id = alb["id"]
            
            # Skip already processed albums
            if album_id in processed_albums:
                continue
                
            album_title = alb.get("title", "Unknown Album")
            album_monitored = alb.get("monitored", False)

            if MONITORED_ONLY and not album_monitored:
                continue

            track_count = alb.get("statistics", {}).get("trackCount", 0)
            track_file_count = alb.get("statistics", {}).get("trackFileCount", 0)
            if track_count > track_file_count:
                # incomplete album
                incomplete_albums.append({
                    "artistId": artist_id,
                    "artistName": artist_name,
                    "albumId": album_id,
                    "albumTitle": album_title,
                    "missing": track_count - track_file_count
                })

    if not incomplete_albums:
        if not processed_albums:
            logger.info("No incomplete albums found.")
        else:
            logger.info("All incomplete albums already processed.")
        return processed_albums

    logger.info(f"Found {len(incomplete_albums)} incomplete album(s).")
    logger.info(f"Processing up to {HUNT_MISSING_ITEMS} albums this cycle.")
    
    processed_count = 0
    used_indices = set()
    newly_processed = []

    # Process albums up to HUNT_MISSING_ITEMS
    while True:
        if processed_count >= HUNT_MISSING_ITEMS:
            logger.info("Reached HUNT_MISSING_ITEMS. Exiting loop.")
            break
        if len(used_indices) >= len(incomplete_albums):
            logger.info("All incomplete albums processed. Exiting loop.")
            break

        # Select next album (randomly or sequentially)
        if RANDOM_SELECTION and len(incomplete_albums) > 1:
            while True:
                idx = random.randint(0, len(incomplete_albums) - 1)
                if idx not in used_indices:
                    break
        else:
            idx_candidates = [i for i in range(len(incomplete_albums)) if i not in used_indices]
            if not idx_candidates:
                break
            idx = idx_candidates[0]

        used_indices.add(idx)
        album_obj = incomplete_albums[idx]
        artist_id = album_obj["artistId"]
        artist_name = album_obj["artistName"]
        album_id = album_obj["albumId"]
        album_title = album_obj["albumTitle"]
        missing = album_obj.get("missing", 0)

        logger.info(f"Processing incomplete album '{album_title}' by '{artist_name}' (missing {missing} tracks)...")

        # Refresh the artist
        refresh_resp = refresh_artist(artist_id)
        if not refresh_resp or "id" not in refresh_resp:
            logger.warning(f"WARNING: Could not refresh artist {artist_name}. Skipping album.")
            time.sleep(10)
            logger.info("⭐ Tool Great? Donate @ https://donate.plex.one for Daughter's College Fund!")
            continue
        logger.info(f"Refresh command accepted (ID={refresh_resp['id']}). Waiting 5s...")
        time.sleep(5)

        # AlbumSearch
        search_resp = album_search(album_id)
        if search_resp and "id" in search_resp:
            logger.info(f"AlbumSearch command accepted (ID={search_resp['id']}).")
            # Add to processed list
            newly_processed.append(album_id)
        else:
            logger.warning(f"WARNING: AlbumSearch command failed for album '{album_title}'.")

        processed_count += 1
        logger.info(f"Album processed.")
    
    # Return updated processed list
    return processed_albums + newly_processed

# ---------------------------
# UPGRADE: Album-Level Logic
# ---------------------------
def get_cutoff_albums() -> List[Dict]:
    """
    Directly query Lidarr's 'wanted/cutoff' endpoint to get albums below cutoff.
    Simplified to match the curl approach.
    """
    try:
        url = f"{API_URL}/api/v1/wanted/cutoff"
        headers = {
            "X-Api-Key": API_KEY,
            "Accept": "application/json",
        }
        params = {
            "pageSize": 100,
            "page": 1
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        if not data or not isinstance(data, dict):
            logger.warning("Invalid response format from wanted/cutoff API")
            return []
        
        records = data.get("records", [])
        if not records:
            logger.info("No cutoff albums returned from API")
            return []
        
        # Only log the count, not each individual album
        logger.info(f"Found {len(records)} album(s) needing upgrade.")
        
        return records
        
    except Exception as e:
        logger.error(f"Error getting cutoff albums: {e}")
        return []

def process_album_upgrades() -> bool:
    """
    Gets albums with quality below cutoff and initiates searches for better quality.
    
    Returns:
        True if any processing was done, False otherwise
    """
    logger.info("=== Checking for Album Quality Upgrades (Cutoff Unmet) ===")
    
    # If HUNT_UPGRADE_ALBUMS is set to 0, skip upgrade processing
    if HUNT_UPGRADE_ALBUMS <= 0:
        logger.info("HUNT_UPGRADE_ALBUMS is set to 0, skipping album upgrades")
        return False
    
    # Get cutoff albums directly from Lidarr's API
    cutoff_albums = get_cutoff_albums()
    
    if not cutoff_albums:
        logger.info("No albums below cutoff found. No upgrades needed.")
        return False

    # Prepare upgrade candidates with needed information
    upgrade_candidates = []
    for album in cutoff_albums:
        album_id = album.get("id")
        album_title = album.get("title", "Unknown Album")
        artist = album.get("artist", {})
        artist_id = artist.get("id")
        artist_name = artist.get("artistName", "Unknown Artist")
        monitored = album.get("monitored", False)
        
        # Skip albums where we can't get IDs
        if not album_id or not artist_id:
            continue
            
        # Skip unmonitored albums if MONITORED_ONLY is enabled
        if MONITORED_ONLY and not monitored:
            logger.debug(f"Skipping unmonitored album: {artist_name} - {album_title}")
            continue
        
        # Add to upgrade candidates
        upgrade_candidates.append({
            "artistId": artist_id,
            "artistName": artist_name,
            "albumId": album_id,
            "albumTitle": album_title
        })
    
    if not upgrade_candidates:
        logger.info("No monitored albums found for upgrade.")
        return False
    
    logger.info(f"Processing {min(HUNT_UPGRADE_ALBUMS, len(upgrade_candidates))} of {len(upgrade_candidates)} candidate album(s) for upgrade")
    
    processed_count = 0
    used_indices = set()

    # Process albums up to HUNT_UPGRADE_ALBUMS
    while True:
        if processed_count >= HUNT_UPGRADE_ALBUMS:
            logger.info(f"Reached HUNT_UPGRADE_ALBUMS={HUNT_UPGRADE_ALBUMS}. Stopping upgrade loop.")
            break
        if len(used_indices) >= len(upgrade_candidates):
            logger.info("All upgrade candidates processed.")
            break

        # Select next album (randomly or sequentially)
        if RANDOM_SELECTION and len(upgrade_candidates) > 1:
            while True:
                idx = random.randint(0, len(upgrade_candidates) - 1)
                if idx not in used_indices:
                    break
        else:
            idx_candidates = [i for i in range(len(upgrade_candidates)) if i not in used_indices]
            if not idx_candidates:
                break
            idx = idx_candidates[0]

        used_indices.add(idx)
        album_obj = upgrade_candidates[idx]
        artist_id = album_obj["artistId"]
        artist_name = album_obj["artistName"]
        album_id = album_obj["albumId"]
        album_title = album_obj["albumTitle"]

        logger.info(f"Upgrading album '{album_title}' by '{artist_name}'...")

        # Refresh the artist first
        ref_resp = refresh_artist(artist_id)
        if not ref_resp or "id" not in ref_resp:
            logger.warning("WARNING: Refresh command failed. Skipping this album.")
            time.sleep(10)
            logger.info("⭐ Tool Great? Donate @ https://donate.plex.one for Daughter's College Fund!")
            continue
        logger.info(f"Refresh accepted (ID={ref_resp['id']}). Waiting 5s...")
        time.sleep(5)

        # Perform album search for better quality
        srch_resp = album_search(album_id)
        if srch_resp and "id" in srch_resp:
            logger.info(f"AlbumSearch command accepted (ID={srch_resp['id']}).")
            processed_count += 1
            logger.info(f"Processed {processed_count}/{HUNT_UPGRADE_ALBUMS} album upgrades this cycle.")
        else:
            logger.warning(f"WARNING: AlbumSearch failed for album ID={album_id}.")
            time.sleep(10)
            logger.info("⭐ Tool Great? Donate @ https://donate.plex.one for Daughter's College Fund!")
            continue

        logger.info(f"Album upgrade processed.")

    logger.info(f"Completed processing {processed_count} album upgrades total in this run.")
    return processed_count > 0

# ---------------------------
# Main Loop
# ---------------------------
def log_configuration():
    """Log the current configuration settings"""
    logger.info("=== Huntarr [Lidarr Edition] Starting ===")
    logger.info(f"API URL: {API_URL}")
    logger.info(f"Missing Content Configuration: HUNT_MISSING_MODE={HUNT_MISSING_MODE}, HUNT_MISSING_ITEMS={HUNT_MISSING_ITEMS}")
    logger.info(f"Upgrade Configuration: HUNT_UPGRADE_ALBUMS={HUNT_UPGRADE_ALBUMS}")
    logger.info(f"State Reset Interval: {STATE_RESET_INTERVAL_HOURS} hours")
    logger.info(f"MONITORED_ONLY={MONITORED_ONLY}, RANDOM_SELECTION={RANDOM_SELECTION}")
    logger.info(f"SLEEP_DURATION={SLEEP_DURATION}s")
    logger.debug(f"API_KEY={API_KEY}")

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
        
        # Sleep at the end of the cycle only
        logger.info(f"Cycle complete. Sleeping {SLEEP_DURATION}s before next cycle...")
        time.sleep(SLEEP_DURATION)
        logger.info("⭐ Tool Great? Donate @ https://donate.plex.one for Daughter's College Fund!")


if __name__ == "__main__":
    # Log configuration settings
    log_configuration()

    try:
        main_loop()
    except KeyboardInterrupt:
        logger.info("Huntarr-Lidarr stopped by user.")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)