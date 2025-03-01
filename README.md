# FRC 1671 QR Code Scanner

### Description
Counterpart Application to ScoutingKindles, written in Python to scan, decode, and upload data from QR codes to the scout-api for further analysis of scout data.

### Usage (Windows)

1. In a terminal, do `python3 main.py`
2. The program should be displaying the live camera feed and processing the frames for QR Codes.
3. Configure API settings after pressing the gear icon in the top left corner.
4. Set the upload type to be either an individual upload or a batch upload.
5. Hold a 1671 QR code up to the camera.
6. Wait to see if the upload was successful.

### Upload types
There are two upload types:
- Individual: Scans and uploads a QR code at the time it was scanned. (This can be slow for scanning many QR codes after another.)

- Batch: Scans and adds the QR code to a list for them to be uploaded all at once when the upload button is pressed. (This is faster and ideal for competitions.)
 
### Shortcuts
- "C" Selects next available camera
- "Ctrl + Alt + C" Clears the terminal
- "Ctrl + Q" Quits the program
- "Ctrl + E" Exports the terminal to a file
- "Ctrl + F" Shows FPS
- "Ctrl + U" Uploads batch
- "Ctrl + R" Refreshes available cameras
- "Ctrl + Backspace" Deletes batch

Double-clicking anywhere on the displayed camera frames will toggle the camera on and off.


### Linux Installation

**If you are on Linux, lucky you! All you have to do is run the `installer.sh`**

1. Download the .zip file from GitHub
2. Unzip the file and `cd` into the newly extracted folder.
2. Do `cd Install/Linux/` to change directory.
4. Do `sudo chmod +x installer.sh` to make it executable.
5. Run `./installer.sh install`

The application should now appear in the application menu. Just click on it to run the program.

### Dependencies
**If you are on Linux, dependencies are automatically installed with the installer.**
 (to-do: specific versioning of each dependancy, according to what is currently stable)
- PyQt6
- Pyzbar
- Cv2
- Requests

### Windows Installation
Donwload and run the .exe from the Releases.
