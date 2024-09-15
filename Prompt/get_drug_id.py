import json
import requests

def get_pubchem_id(compound_name):
    try:
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{compound_name}/cids/JSON"
        response = requests.get(url)
        response.raise_for_status()  # Ensure we raise an error for bad responses
        cids = response.json().get('IdentifierList', {}).get('CID', [])
        
        if cids:
            cid = cids[0]
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON/"
            response = requests.get(url)
            response.raise_for_status()
            sections = response.json().get('Record', {}).get('Section', [])
            for section in sections:
                if section.get('TOCHeading') == 'External Sources':
                    for subsection in section.get('Section', []):
                        if subsection.get('TOCHeading') == 'PubChem':
                            return subsection.get('Information', [{}])[0].get('Value', {}).get('StringWithMarkup', [{}])[0].get('String', '')
        return cid
    except requests.RequestException as e:
        print(f"An error occurred: {e}")
        return None

def read_compounds(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError as e:
        print(f"File not found: {e}")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return {}

def match_pubchem_ids(compounds):
    result = {}
    for category, names in compounds.items():
        result[category] = {}
        for name in names:
            drugbank_id = get_pubchem_id(name)
            result[category][name] = drugbank_id
            print(f"Matched {name} to CID: {drugbank_id}")
    return result

# Update the file path as needed
compounds_file_path = 'Folic Acid Metabolism PMC analysis/FA_Metabolism_Drug.json'
compounds = read_compounds(compounds_file_path)
if compounds:
    matched_ids = match_pubchem_ids(compounds)

    with open('matched_pubchem_ids.json', 'w') as file:
        json.dump(matched_ids, file, indent=4)
else:
    print("No compounds to process.")
