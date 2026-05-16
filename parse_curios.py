from bs4 import BeautifulSoup
import re
import json

def clean_text(text):
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def item_from_images(images):
    for img in images:
        img_lower = img.lower()
        if 'bandage' in img_lower:
            return 'Bandage'
        elif 'holy_water' in img_lower:
            return 'Holy Water'
        elif 'shovel' in img_lower:
            return 'Shovel'
        elif 'herb' in img_lower:
            return 'Medicinal Herbs'
        elif 'antivenom' in img_lower:
            return 'Antivenom'
        elif 'skeleton_key' in img_lower:
            return 'Skeleton Key'
        elif 'the_blood' in img_lower:
            return 'The Blood'
        elif 'torch' in img_lower:
            return 'Torch'
        elif 'dog_treat' in img_lower:
            return 'Dog Treats'
        elif 'byhand' in img_lower or 'nothing.curio' in img_lower or 'redcross' in img_lower:
            return 'Nothing'
    return ''

def parse_curios_final(html_path):
    with open(html_path, 'r') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    span = soup.find('span', id='Curios')
    if not span:
        return []
    
    curios_heading = span.find_parent(['h2', 'h1'])
    if not curios_heading:
        return []

    tables = []
    sibling = curios_heading.find_next_sibling()
    while sibling and sibling.name not in ['h2', 'h1']:
        if sibling.name == 'table':
            tables.append(sibling)
        sibling = sibling.find_next_sibling()

    all_curios = []
    current_curio = None
    current_item = ''
    
    for table in tables:
        rows = table.find_all('tr')
        if len(rows) < 2:
            continue

        for row in rows[1:]:
            cells = row.find_all(['td', 'th'])
            num_cells = len(cells)
            
            cell_data = []
            for cell in cells:
                imgs = [img.get('src', '').split('/')[-1].split('?')[0] for img in cell.find_all('img')]
                text = clean_text(cell.get_text())
                cell_data.append({'text': text, 'images': imgs})
            
            if num_cells == 7:
                curio_name = cell_data[2]['text']
                current_curio = {'name': curio_name, 'interactions': []}
                all_curios.append(current_curio)
                current_item = item_from_images(cell_data[3]['images']) or cell_data[3]['text']
                chance = cell_data[4]['text']
                result = cell_data[5]['text']
                desc = cell_data[6]['text']
                
            elif num_cells == 6:
                curio_name = cell_data[1]['text']
                current_curio = {'name': curio_name, 'interactions': []}
                all_curios.append(current_curio)
                current_item = item_from_images(cell_data[2]['images']) or cell_data[2]['text']
                chance = cell_data[3]['text']
                result = cell_data[4]['text']
                desc = cell_data[5]['text']
                
            elif num_cells == 5:
                curio_name = cell_data[0]['text']
                current_curio = {'name': curio_name, 'interactions': []}
                all_curios.append(current_curio)
                current_item = item_from_images(cell_data[1]['images']) or cell_data[1]['text']
                chance = cell_data[2]['text']
                result = cell_data[3]['text']
                desc = cell_data[4]['text']
                
            elif num_cells == 4:
                current_item = item_from_images(cell_data[0]['images']) or cell_data[0]['text']
                chance = cell_data[1]['text']
                result = cell_data[2]['text']
                desc = cell_data[3]['text']
                
            elif num_cells == 3:
                chance = cell_data[0]['text']
                result = cell_data[1]['text']
                desc = cell_data[2]['text']
                
            else:
                continue
            
            if current_curio and result:
                current_curio['interactions'].append({
                    'item': current_item,
                    'chance': chance,
                    'result': result,
                    'description': desc
                })

    return all_curios

def extract_curio_name(full_text):
    # Extract just the curio name from text like "Pile of Strange BonesHaunted, Knowledge..."
    # The name is the first part before the description/tags start
    # Tags are typically capitalized words or known keywords
    known_tags = ['Haunted', 'Knowledge', 'Scrounging', 'Unholy', 'CCrave', 'Drink', 
                  'Fountain', 'Body', 'Food', 'Reflective', 'Torture', 'Treasure',
                  'A heap', 'The soil', 'A bubbling', 'Mouldering', 'An anachronistic',
                  'A mysterious', 'Shifting', 'The hive', 'You can', 'This appears',
                  'Bottles', 'This chest', 'Only appears', 'Take up', 'Tantalizing',
                  'Glittering', 'The fireplace', 'Useful', 'This anguished']
    
    # Try to find the first sentence break or tag
    for tag in known_tags:
        if tag in full_text:
            idx = full_text.index(tag)
            return full_text[:idx].strip()
    
    # Fallback: just return the text
    return full_text

def extract_description(full_text, name):
    desc = full_text[len(name):].strip()
    # Remove trailing "See also..." references
    desc = re.sub(r'See also.*', '', desc).strip()
    return desc if desc else None

def clean_and_group(curios):
    cleaned = []
    for curio in curios:
        name = extract_curio_name(curio['name'])
        desc = extract_description(curio['name'], name)
        
        # Group interactions by item
        grouped = {}
        for inter in curio['interactions']:
            item = inter['item']
            if item not in grouped:
                grouped[item] = []
            grouped[item].append(inter)
        
        interactions = []
        for item, outcomes in grouped.items():
            interactions.append({
                'item': item,
                'outcomes': outcomes
            })
        
        cleaned.append({
            'name': name,
            'description': desc,
            'interactions': interactions
        })
    
    return cleaned

# Parse and clean
for location, path in [('Courtyard', 'darkestdungeon_wiki/Courtyard.html'), ('Farmstead', 'darkestdungeon_wiki/Farmstead.html')]:
    raw = parse_curios_final(path)
    cleaned = clean_and_group(raw)
    print(f"\n=== {location} ({len(cleaned)} curios) ===")
    for c in cleaned:
        print(f"\n{c['name']}")
        if c['description']:
            print(f"  Description: {c['description'][:80]}")
        for inter in c['interactions']:
            print(f"  Item: {inter['item']}")
            for o in inter['outcomes']:
                print(f"    {o['chance']}: {o['result']}")
