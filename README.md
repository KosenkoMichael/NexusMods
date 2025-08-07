# Nexus mod manager installation guide

## 1
Download latest python sdk version</br></t>https://www.python.org/downloads/ and add it to PATH
## 2 
Download chrome extension</br></t>https://chromewebstore.google.com/detail/ojfebgpkimhlhcblbalbfjblapadhbol?utm_source=item-share-cb
## 3 
Log in on</br></t>https://www.nexusmods.com/
## 4 
While logged in, save cookies to clipboard
## 5
Create cookies.json in the folder you downloaded and copy the cookies there
## 6
open config.py in text editor and set:</br>
* MOD_NAME_TO_ID - each string = pare </br>[mod name as in mod_load_order.txt : mod_id as on nexusmods] (a few mods added as example)
* MOD_LIST_FILE = path to mod_load_order.txt
* MODS_FOLDER = path to folder with mods
* GAME_DOMAIN = game name as on nexusmods
## 7
run init.bat