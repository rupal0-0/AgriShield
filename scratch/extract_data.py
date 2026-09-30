import re
import json
import os

html_path = 'agrishield_dataset_website.html'
json_path = 'data/agrishield_records.json'

if not os.path.exists('data'):
    os.makedirs('data')

with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Look for const RECORDS = [...];
match = re.search(r'const RECORDS = (\[.*?\]);', content, re.DOTALL)
if match:
    records_str = match.group(1)
    # The string is valid JS but might need some cleaning for JSON
    # However, usually these dumps are valid JSON.
    try:
        records = json.loads(records_str)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(records, f)
        print(f"Successfully extracted {len(records)} records to {json_path}")
    except Exception as e:
        print(f"Error parsing JSON: {e}")
else:
    print("RECORDS not found in HTML")
