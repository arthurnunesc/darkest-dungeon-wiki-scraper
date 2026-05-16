import os
import urllib.request
import time

BASE_URL = 'https://darkestdungeon.wiki.gg'
PROJECT_DIR = '/Users/arthur/Developer/darkest-companion'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

curio_icons = [
    ('pile_of_strange_bones.png', '/images/thumb/Pile_of_Strange_Bones.png/180px-Pile_of_Strange_Bones.png'),
    ('bloodflowers.png', '/images/thumb/Bloodflowers.png/164px-Bloodflowers.png'),
    ('damned_fountain.png', '/images/thumb/Damned_Fountain.png/180px-Damned_Fountain.png'),
    ('disturbing_diversion.png', '/images/thumb/Disturbing_Diversion.png/180px-Disturbing_Diversion.png'),
    ('forgotten_delicacies.png', '/images/thumb/Forgotten_Delicacies.png/180px-Forgotten_Delicacies.png'),
    ('hooded_shrew.png', '/images/thumb/Hooded_Shrew.png/131px-Hooded_Shrew.png'),
    ('throbbing_cocoons.png', '/images/thumb/Throbbing_Cocoons.png/180px-Throbbing_Cocoons.png'),
    ('thronging_hive.png', '/images/thumb/Thronging_Hive.png/180px-Thronging_Hive.png'),
    ('wine_crate.png', '/images/thumb/Wine_Crate.png/180px-Wine_Crate.png'),
    ('wizened_shrew.png', '/images/thumb/Wizened_Shrew.png/107px-Wizened_Shrew.png'),
    ('winemakers_reserve.png', '/images/thumb/Winemaker%27s_Reserve.png/180px-Winemaker%27s_Reserve.png'),
    ('lost_treasure_box.png', '/images/thumb/Lost_Treasure_Box.png/180px-Lost_Treasure_Box.png'),
    ('trinket_chest.png', '/images/thumb/Trinket_Chest.png/180px-Trinket_Chest.png'),
    ('corrupted_harvest.png', '/images/thumb/Corrupted_Harvest.png/176px-Corrupted_Harvest.png'),
    ('fresh_harvest.png', '/images/thumb/Fresh_Harvest.png/172px-Fresh_Harvest.png'),
    ('gleaming_shards.png', '/images/thumb/Gleaming_Shards.png/131px-Gleaming_Shards.png'),
    ('millers_hearth.png', '/images/thumb/Miller%27s_Hearth.png/111px-Miller%27s_Hearth.png'),
    ('plentiful_bounty.png', '/images/thumb/Plentiful_Bounty.png/122px-Plentiful_Bounty.png'),
    ('rotted_fare.png', '/images/thumb/Rotted_Fare.png/180px-Rotted_Fare.png'),
    ('stockpile.png', '/images/thumb/Stockpile.png/103px-Stockpile.png'),
    ('mildred.png', '/images/thumb/Mildred.png/76px-Mildred.png'),
]

provision_icons = [
    ('The_Blood.png', '/images/thumb/The_Blood.png/100px-The_Blood.png'),
]

def download(url, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            with open(dest, 'wb') as f:
                f.write(response.read())
        size = os.path.getsize(dest)
        print(f'  OK: {os.path.basename(dest)} ({size} bytes)')
        return True
    except Exception as e:
        print(f'  FAIL: {os.path.basename(dest)} - {e}')
        return False

print('Downloading curio icons...')
for filename, path in curio_icons:
    url = BASE_URL + path
    dest = f'{PROJECT_DIR}/static/icons/curios/{filename}'
    download(url, dest)
    time.sleep(1.5)

print('\nDownloading provision icons...')
for filename, path in provision_icons:
    url = BASE_URL + path
    dest = f'{PROJECT_DIR}/static/icons/provisions/{filename}'
    download(url, dest)
    time.sleep(1.5)

print('\nDone!')
