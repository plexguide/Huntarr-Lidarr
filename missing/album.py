#!/usr/bin/env python3
"""
Album Mode Missing Logic
Handles processing for missing content in album mode
"""

import random
import time
from typing import List, Dict, Any
from utils.logger import logger
from config import HUNT_MISSING_ITEMS, SLEEP_DURATION, MONITORED_ONLY, RANDOM_SELECTION
from api import get_artists_json, get_albums_for_artist, refresh_artist, album_search

def process_albums_missing(processed_albums: List[int] = None) -> List[int]:
    """
    Process albums with missing tracks
    
    Args:
        processed_albums: List of album IDs already processed
        
    Returns:
        Updated list of processed album IDs
    """
    logger.info("=== Running in ALBUM MODE (Missing) ===")
    
    if processed_albums is None:
        processed_albums = []
    
    # Skip if HUNT_MISSING_ITEMS is set to 0
    if HUNT_MISSING_ITEMS <= 0:
        logger.info("HUNT_MISSING_ITEMS is set to 0, skipping album missing content")
        return processed_albums
        
    artists = get_artists_json()
    if not artists:
        logger.error("ERROR: No artist data. 60s wait...")
        time.sleep(60)
        logger.info("⭐ Tool Great? Donate @ https://donate.plex.one for Daughter's College Fund!")
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
            logger.info("No incomplete albums found. 60s wait...")
            time.sleep(60)
            logger.info("⭐ Tool Great? Donate @ https://donate.plex.one for Daughter's College Fund!")
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
        logger.info(f"Album processed. Sleeping {SLEEP_DURATION}s...")
        logger.info("⭐ Tool Great? Donate @ https://donate.plex.one for Daughter's College Fund!")
        time.sleep(SLEEP_DURATION)
    
    # Return updated processed list
    return processed_albums + newly_processed