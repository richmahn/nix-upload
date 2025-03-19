# nix-upload
Given a directory on your computer, this script will locate all photos (recursively) under that directory, and upload all of the photos to a specified nixplay playlist.

## To install:
1. Install python (I have tested with python 3.13.2 on Windows 11)
2. Install selenium and webdriver-manager
	- pip install selenium
	- pip install webdriver-manager
3. Manually login to the nixplay website (https://app.nixplay.com), create a playlist called "nix-upload" (without the quotes in the name), and associate this playlist with your digital photo frame(s)	
4. Create a directory called "nix-upload" on your computer
5. Into this directory
	- copy the sample_config.json file from github as config.json and then edit the file with your settings
	- copy the nix-upload.py file
	
## To run:
1. open a command shell in the "nix-upload" directory on your computer
2. Run "python nix-upload.py"

## NOTE
The script will first DELETE ALL PHOTOS from the specified playlist. Then it will upload all the new photos to the same playlist.

## Known issues:
- I dont know why this warning shows, but it seems to be a benign message
"Attempting to use a delegate that only supports static-sized tensors with a graph that has dynamic-sized tensors (tensor#-1 is a dynamic-sized tensor)."
- In your config.json file, set "max_photos" to not more than 1900, and "batch_size" to not more than 100, for best performance


## Disclaimer
USE AT YOUR OWN RISK

