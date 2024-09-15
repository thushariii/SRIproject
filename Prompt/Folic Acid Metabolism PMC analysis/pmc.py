import json
import os
import re
import fuzzywuzzy

# Print a separator line for readability in the console output
print("\n" + "-" * 50 + "\n")

# Load drug and protein names from JSON files
with open("Folic Acid Metabolism PMC analysis\FA_Metabolism_Drug.json", "r", encoding="utf-8") as D:
    drug_names_dict = json.load(D)
with open("Folic Acid Metabolism PMC analysis\protein_names_dict.json", "r", encoding="utf-8") as D:
    protein_names_dict = json.load(D)
    
# Define the directories for the query files and PMC download files
query_dir = r"Folic Acid Metabolism PMC analysis\PMC_query"
pmc_dir = r"Folic Acid Metabolism PMC analysis\PMC_download"

# Initialize a counter for the number of matches found
i = 0

# Iterate over each file in the query directory
for query_file in os.listdir(query_dir):
    query_file_path = os.path.join(query_dir, query_file)
    with open(query_file_path, "r", encoding="utf-8") as q:
        queries = json.load(q)
        
    # Extract protein and drug IDs from the filename
    protein_id = query_file.split("_")[0]
    drug_id = query_file.split("_")[1].split(".")[0]

    # Obtain the drug and protein name lists from the dictionaries
    protein_names = protein_names_dict.get(protein_id, [])
    drug_names = drug_names_dict.get(drug_id, [])

    # Iterate over each query in the query file
    for query in queries:
        protein_name_query = query["Query_ProteinName"]
        drug_name_query = query["Query_DrugName"]
        pmc_id = query["PMC"]
        
        # Construct the path to the corresponding PMC file
        pmc_file_path = os.path.join(pmc_dir, pmc_id + ".html")
        
        if os.path.exists(pmc_file_path):
            with open(pmc_file_path, "r", encoding="utf-8") as P:
                pmc_content = P.read()
                
                # Perform exact word match for the drug and protein names in the PMC content
                found_proteins = [name for name in protein_names if re.search(re.escape(name), pmc_content, re.IGNORECASE)]
                found_drugs = [name for name in drug_names if re.search(re.escape(name), pmc_content, re.IGNORECASE)]

                # Perform fuzzy matching for the drug and protein names in the PMC content
                for protein in protein_names:
                    if fuzzywuzzy.fuzz.partial_ratio(protein, protein_name_query) > 90:
                        found_proteins.append(protein)


                for drug in drug_names:
                    if fuzzywuzzy.fuzz.partial_ratio(drug, drug_name_query) > 90:
                        found_drugs.append(drug)

                # Print found drugs and proteins if both are found in the content
                if found_proteins and found_drugs:
                    i += 1
                    print(f"Number: {i}, PMC ID: {pmc_id}")
                    print(f"Found Proteins: {', '.join(found_proteins)}")
                    print(f"Found Drugs: {', '.join(found_drugs)}")
                    print("\n" + "-" * 50 + "\n")