#!/usr/bin/env python3
"""
Artist Mode Missing Logic
Handles processing for missing content in artist mode
"""

import random
import time
from typing import List, Dict, Any
from utils.logger import logger
from config import HUNT_MISSING_ITEMS, SLEEP_DURATION, MONITORED_ONLY, RANDOM_SELECTION
from api import get_artists_json, refresh_artist, missing_album_search, lidarr_request

def process_artists_missing(processed_artists: List[int] = None) -> List[int]:
    """
    Process artists with missing tracks
    
    Args:
        processed_artists: List of artist IDs already processed
        
    Returns:
        Updated list of processed artist IDs
    """
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
            logger.info("No incomplete artists found. Waiting 60s...")
            time.sleep(60)
            logger.info("⭐ Tool Great? Donate @ https://donate.plex.one for Daughter's College Fund!")
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
        logger.info(f"Processed artist. Sleeping {SLEEP_DURATION}s...")
        logger.info("⭐ Tool Great? Donate @ https://donate.plex.one for Daughter's College Fund!")
        time.sleep(SLEEP_DURATION)
    
    # Return updated processed list
    return processed_artists + newly_processed