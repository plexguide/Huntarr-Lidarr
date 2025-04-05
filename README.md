# Huntarr [Lidarr Edition] - Force Lidarr to Hunt Missing Music & Upgrade Music Qualities

<h2 align="center">Want to Help? Click the Star in the Upper-Right Corner! ⭐</h2>

<table>
  <tr>
    <td colspan="2"><img src="https://github.com/user-attachments/assets/122f7207-b706-4b8d-8845-f21a86f9bf77" width="100%"/></td>
  </tr>
</table>


**NOTE**: This utilizes Lidarr API Version - `1`.
 
## Table of Contents
- [Overview](#overview)
- [Related Projects](#related-projects)
- [Features](#features)
- [How It Works](#how-it-works)
- [Configuration Options](#configuration-options)
- [Installation Methods](#installation-methods)
  - [Docker Run](#docker-run)
  - [Docker Compose](#docker-compose)
  - [Unraid Users](#unraid-users)
  - [SystemD Service](#systemd-service)
- [Use Cases](#use-cases)
- [Tips](#tips)
- [Troubleshooting](#troubleshooting)

## Overview 

This script continually searches your Lidarr library for missing music (artists/albums) and music that needs quality upgrades. It automatically triggers searches for both missing content and albums below your quality cutoff. It's designed to run continuously while being gentle on your indexers, helping you gradually complete your music collection with the best available quality.

## Related Projects

* [Huntarr - Sonarr Edition](https://github.com/plexguide/Sonarr-Hunter) - Sister version for TV shows
* [Huntarr - Radarr Edition](https://github.com/plexguide/Radarr-Hunter) - Sister version for movies
* [Unraid Intel ARC Deployment](https://github.com/plexguide/Unraid_Intel-ARC_Deployment) - Convert videos to AV1 Format (I've saved 325TB encoding to AV1)
* Visit [PlexGuide](https://plexguide.com) for more great scripts

## PayPal Donations – Building My Daughter's Future

My 12-year-old daughter is passionate about singing, dancing, and exploring STEM. She consistently earns A-B honors and dreams of a bright future. Every donation goes directly into her college fund, helping turn those dreams into reality. Thank you for your generous support!

[![Donate with PayPal button](https://www.paypalobjects.com/en_US/i/btn/btn_donate_LG.gif)](https://www.paypal.com/donate?hosted_button_id=58AYJ68VVMGSC)

## Features

- 🔄 **Continuous Operation**: Runs indefinitely until manually stopped
- 🎯 **Dual Targeting System**: Targets both missing music and quality upgrades
- 🎲 **Random Selection**: By default, selects music randomly to distribute searches across your library
- ⏱️ **Throttled Searches**: Includes configurable delays to prevent overloading indexers
- 📊 **Status Reporting**: Provides clear feedback about what it's doing and which music it's searching for
- 🛡️ **Error Handling**: Gracefully handles connection issues and API failures
- 🔁 **State Tracking**: Remembers which artists/albums have been processed to avoid duplicate searches
- ⚙️ **Configurable Reset Timer**: Automatically resets search history after a configurable period

## How It Works

1. **Initialization**: Connects to your Lidarr instance and analyzes your library
2. **Missing Music**: 
   - Identifies artists or albums without files (based on configured mode)
   - Randomly selects content to process (up to configurable limit)
   - Refreshes metadata and triggers searches
3. **Quality Upgrades**:
   - Finds albums that don't meet your quality cutoff settings
   - Processes them in configurable batches
   - Uses smart selection to distribute searches
4. **State Management**:
   - Tracks which artists/albums have been processed
   - Automatically resets this tracking after a configurable time period
5. **Repeat Cycle**: Waits for a configurable period before starting the next cycle

<table>
  <tr>
    <td width="50%">
      <img src="https://github.com/user-attachments/assets/ef212161-e14c-484c-b6a1-20986022a2c3" width="100%"/>
      <p align="center"><em>Missing Movies Demo</em></p>
    </td>
    <td width="50%">
      <img src="https://github.com/user-attachments/assets/4843b80b-ea1f-4ff0-b76f-8187e3912883" width="100%"/>
      <p align="center"><em>Quality Upgrade Demo</em></p>
    </td>
  </tr>
  <tr>
    <td colspan="2">
      <img src="https://github.com/user-attachments/assets/3e95f6d5-4a96-4bb8-a5b9-1d7b871ff94a" width="100%"/>
      <p align="center"><em>State Management System</em></p>
    </td>
  </tr>
</table>

## Configuration Options

The following environment variables can be configured:

| Variable                     | Description                                                                | Default    |
|------------------------------|----------------------------------------------------------------------------|------------|
| `API_KEY`                    | Your Lidarr API key                                                        | Required   |
| `API_URL`                    | URL to your Lidarr instance                                                | Required   |
| `HUNT_MISSING_MODE`          | Mode for missing searches: `"artist"`, `"album"`, or `"both"`              | artist     |
| `HUNT_MISSING_ITEMS`         | Maximum missing items to process per cycle (0 to disable)                  | 1          |
| `HUNT_UPGRADE_ALBUMS`        | Maximum albums to upgrade per cycle (0 to disable)                         | 0          |
| `SLEEP_DURATION`             | Seconds to wait after completing a cycle (900 = 15 minutes)                | 900        |
| `RANDOM_SELECTION`           | Use random selection (`true`) or sequential (`false`)                      | true       |
| `MONITORED_ONLY`             | Only process monitored content                                             | true       |
| `STATE_RESET_INTERVAL_HOURS` | Hours after which the processed state files reset (168=1 week, 0=never)    | 168        |
| `DEBUG_MODE`                 | Enable detailed debug logging (`true` or `false`)                          | false      |

### Detailed Configuration Explanation

- **HUNT_MISSING_MODE**
  - Determines the level at which missing content is processed
  - Options:
    - `"artist"`: Process at the artist level (search for all missing albums by artist)
    - `"album"`: Process at the album level (search for individual missing albums)
    - `"both"`: Process both artists and albums with missing content

- **HUNT_MISSING_ITEMS**
  - Sets the maximum number of missing items (artists or albums) to process in each cycle
  - Setting to `0` disables missing content searches completely

- **HUNT_UPGRADE_ALBUMS**
  - Sets the maximum number of albums to process for quality upgrades in each cycle
  - Setting to `0` disables quality upgrade searches completely

- **STATE_RESET_INTERVAL_HOURS**
  - Controls how often the script "forgets" which items it has already processed
  - Default is 168 hours (one week)
  - Set to `0` to disable reset (always remember processed items)

## Installation Methods

### Docker Run

The simplest way to run Huntarr is via Docker:

```bash
docker run -d --name huntarr-lidarr \
  --restart always \
  -e API_KEY="your-api-key" \
  -e API_URL="http://your-lidarr-address:8686" \
  -e HUNT_MISSING_MODE="album" \
  -e HUNT_MISSING_ITEMS="1" \
  -e HUNT_UPGRADE_ALBUMS="1" \
  -e SLEEP_DURATION="900" \
  -e RANDOM_SELECTION="true" \
  -e MONITORED_ONLY="true" \
  -e STATE_RESET_INTERVAL_HOURS="168" \
  -e DEBUG_MODE="false" \
  huntarr/4lidarr:latest
```

To check on the status of the program, you should see new files downloading or you can type:
```bash
docker logs huntarr-lidarr
```

### Docker Compose

For those who prefer Docker Compose, add this to your `docker-compose.yml` file:

```yaml
version: "3.8"
services:
  huntarr-lidarr:
    image: huntarr/4lidarr:latest
    container_name: huntarr-lidarr
    restart: always
    environment:
      API_KEY: "your-api-key"
      API_URL: "http://your-lidarr-address:8686"
      HUNT_MISSING_MODE: "album"
      HUNT_MISSING_ITEMS: "1"
      HUNT_UPGRADE_ALBUMS: "1"
      SLEEP_DURATION: "900"
      RANDOM_SELECTION: "true"
      MONITORED_ONLY: "true"
      STATE_RESET_INTERVAL_HOURS: "168"
      DEBUG_MODE: "false"
```

Then run:

```bash
docker-compose up -d huntarr-lidarr
```

### Unraid Users

Run from the Unraid Command Line:

```bash
docker run -d --name huntarr-lidarr \
  --restart always \
  -e API_KEY="your-api-key" \
  -e API_URL="http://your-lidarr-address:8686" \
  -e HUNT_MISSING_MODE="album" \
  -e HUNT_MISSING_ITEMS="1" \
  -e HUNT_UPGRADE_ALBUMS="1" \
  -e SLEEP_DURATION="900" \
  -e RANDOM_SELECTION="true" \
  -e MONITORED_ONLY="true" \
  -e STATE_RESET_INTERVAL_HOURS="168" \
  -e DEBUG_MODE="false" \
  huntarr/4lidarr:latest
```

### SystemD Service

For a more permanent installation on Linux systems using SystemD:

1. Save the script to `/usr/local/bin/huntarr-lidarr.sh`
2. Make it executable: `chmod +x /usr/local/bin/huntarr-lidarr.sh`
3. Create a systemd service file at `/etc/systemd/system/huntarr-lidarr.service`:

```ini
[Unit]
Description=Huntarr Lidarr Service
After=network.target lidarr.service

[Service]
Type=simple
User=your-username
Environment="API_KEY=your-api-key"
Environment="API_URL=http://localhost:8686"
Environment="HUNT_MISSING_MODE=album"
Environment="HUNT_MISSING_ITEMS=1"
Environment="HUNT_UPGRADE_ALBUMS=1"
Environment="SLEEP_DURATION=900"
Environment="RANDOM_SELECTION=true"
Environment="MONITORED_ONLY=true"
Environment="STATE_RESET_INTERVAL_HOURS=168"
Environment="DEBUG_MODE=false"
ExecStart=/usr/local/bin/huntarr-lidarr.sh
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

4. Enable and start the service:

```bash
sudo systemctl enable huntarr-lidarr
sudo systemctl start huntarr-lidarr
```

## Use Cases

- **Library Completion**: Gradually fill in missing albums and tracks in your collection
- **Quality Improvement**: Automatically upgrade album quality as better versions become available
- **New Artist Setup**: Automatically find music for newly added artists
- **Background Service**: Run it in the background to continuously maintain your library
- **Smart Rotation**: With state tracking, ensures all content gets attention over time

## Tips

- **First-Time Use**: Start with default settings to ensure it works with your setup
- **Adjusting Speed**: Lower the `SLEEP_DURATION` to search more frequently (be careful with indexer limits)
- **Focus on Missing or Upgrades**: Adjust `HUNT_MISSING_ITEMS` and `HUNT_UPGRADE_ALBUMS` to focus on what matters to you
- **Choose the Right Mode**:
  - Use `artist` mode for broad searches (fastest but less targeted)
  - Use `album` mode for more targeted searches
- **System Resources**: The script uses minimal resources and can run continuously on even low-powered systems
- **Debugging Issues**: Enable `DEBUG_MODE=true` temporarily to see detailed logs when troubleshooting

## Troubleshooting

- **API Key Issues**: Check that your API key is correct in Lidarr settings
- **Connection Problems**: Ensure the Lidarr URL is accessible from where you're running the script
- **Command Failures**: If search commands fail, try using the Lidarr UI to verify what commands are available in your version
- **Logs**: Check the container logs with `docker logs huntarr-lidarr` if running in Docker
- **Debug Mode**: Enable `DEBUG_MODE=true` to see detailed API responses and process flow
- **State Files**: The script stores state in the container - if something seems stuck, try restarting the container

---

**Change Log:**
- **v1**: Original code written
- **v2**: Added dual targeting for both missing and quality upgrade albums
- **v3**: Added state tracking to prevent duplicate searches
- **v4**: Implemented configurable state reset timer
- **v5**: Added debug mode and improved error handling
- **v6**: Enhanced random selection mode for better distribution
- **v7**: Renamed from "Lidarr Hunter" to "Huntarr [Lidarr Edition]"

---

This script helps automate the tedious process of finding missing music and quality upgrades in your collection, running quietly in the background while respecting your indexers' rate limits.