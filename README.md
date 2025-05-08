# Rclone Cloud Mounter
Rclone Cloud Mounter helps you mount cloud storage in your local PC using rclone.

## Requirements

- [Rclone](https://rclone.org/downloads/)

## Installation

1. Download the latest release package from:
   https://github.com/asurpbs/Cloud-Drive-Mounter/releases/download/cloud-drive-mounter/cloud-drive-mounter-v-1.0.0.7z
2. Extract the downloaded archive
3. Configure your cloud drives using rclone (see Usage section below)
4. Run the application and select your configured cloud drive

## Usage

1. **Setting up cloud drives**:
   - You must configure your cloud drives with rclone before using this application
   - To configure a new drive, open Command Prompt or PowerShell and run: `rclone config`
   - Follow the interactive prompts to add your cloud storage account
   - For detailed setup instructions, watch this tutorial: https://www.youtube.com/watch?v=MwxbX6PNiWA

2. **Mounting drives**:
   - Run the Rclone Mount Manager application
   - Choose the number corresponding to the cloud storage you want to mount
   - Press Enter and wait for the mount process to complete
   - Important: Keep the application window open while using your cloud storage

3. **Unmounting drives**:
   - To unmount, close the application window when you're done using the drive

## Note

This application is a front-end for rclone. All mounting operations are performed using rclone in the background.
