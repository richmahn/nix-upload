# nix-upload
Given a directory on your computer, this script will locate all photos (recursively) under that directory, and upload all of the photos to a specified nixplay playlist.

To install:
1. Install python (I have tested with python 3.13.2 on Windows 11)
2. Install selenium and webdriver-manager
	pip install selenium
	pip install webdriver-manager
3. Manually login to the nixplay website (https://app.nixplay.com), create a playlist called "nix-upload" (without the quotes in the name), and associate this playlist with your digital photo frame(s)	
4. Create a directory called "nix-upload" on your computer
5. Into this directory
	2a. copy the sample_config.json file from github as config.json and then edit the file with your settings
	2b. copy the nix-upload.py file
	
	
To run:
1. open a command shell in the "nix-upload" directory on your computer
2. Run "python nix-upload.py"

