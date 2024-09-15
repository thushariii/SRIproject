
import os
import json
import re
import pandas as pd
from bs4 import BeautifulSoup
import fuzzywuzzy.fuzz
import matplotlib.pyplot as plt

# Define the directories for the query files and PMC download files
path = 'Folic Acid Metabolism PMC analysis'
query_dir = r"PMC_query"
pmc_dir = r"PMC_download"
query_dir = os.path.join(path, query_dir)
pmc_dir = os.path.join(path, pmc_dir)

# Load protein and drug names dictionaries
with open('Folic Acid Metabolism PMC analysis/protein_names_dict.json', 'r') as file:
    protein_names_dict = json.load(file)

with open('Folic Acid Metabolism PMC analysis/FA_Metabolism_Drug.json', 'r') as file:
    drug_names_dict = json.load(file)

# pubchem ids
with open('matched_pubchem_ids.json', 'r') as file:
    pubchem_ids = json.load(file)

def filter_papers(save_dir):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    i = 0
    ctr = 0
    metadata = []
    
    fuzzy_agrees_exact = 0 # fuzzy match and exact match
    fuzzy_no_exact = 0 # fuzzy match but no exact match
    exact_no_fuzzy = 0 # exact match but no fuzzy match

    #  Loop through all the query files
    for query_file in os.listdir(query_dir):
        query_file_path = os.path.join(query_dir, query_file)
        with open(query_file_path, "r", encoding="utf-8") as q:
            queries = json.load(q)


        protein_id = query_file.split("_")[0]
        drug_id = query_file.split("_")[1].split(".")[0]
        pubchem_id = pubchem_ids[drug_id]
        vals = []
        for val in pubchem_id.keys():
            if val is not None:
                vals.append(val)
        protein_names = protein_names_dict.get(protein_id, []) + [protein_id]
        drug_names = drug_names_dict.get(drug_id, []) + [drug_id] + vals

        for query in queries:
            protein_name_query = query["Query_ProteinName"]
            drug_name_query = query["Query_DrugName"]
            pmc_id = query["PMC"]
            
            pmc_file_path = os.path.join(pmc_dir, pmc_id + ".html")
            
            if os.path.exists(pmc_file_path):
                with open(pmc_file_path, "r", encoding="utf-8") as P:
                    pmc_content = P.read()
                    pmc_parsed = BeautifulSoup(pmc_content, "html.parser").get_text(separator=" ", strip=True)
                    fuzzy_match_protein = []
                    fuzzy_match_drug = []
                    exact_match_protein = []
                    exact_match_drug = []
                    found_proteins = []
                    for protein in protein_names:
                        if fuzzywuzzy.fuzz.partial_ratio(protein, pmc_parsed) > 90:
                            found_proteins.append(protein)
                            fuzzy_match_protein.append(protein)
                            break
                    found_drugs = []
                    for drug in drug_names:
                        if fuzzywuzzy.fuzz.partial_ratio(drug, pmc_parsed) > 90:
                            found_drugs.append(drug)
                            fuzzy_match_drug.append(drug)
                            break

                    found_proteins.extend([name for name in protein_names if re.search(re.escape(name), pmc_content, re.IGNORECASE)])
                    found_drugs.extend([name for name in drug_names if re.search(re.escape(name), pmc_content, re.IGNORECASE)])
                    exact_match_protein = [name for name in protein_names if re.search(re.escape(name), pmc_content, re.IGNORECASE)]
                    exact_match_drug = [name for name in drug_names if re.search(re.escape(name), pmc_content, re.IGNORECASE)]

                    


                    if found_proteins and found_drugs:
                        i += 1
                        print(f"Number: {i}, PMC ID: {pmc_id}")

                        print(f"Found Proteins: {', '.join(found_proteins)}")
                        print(f"Found Drugs: {', '.join(found_drugs)}")
                        print("\n" + "-" * 50 + "\n")

                        save_file_path = os.path.join(save_dir, f"{protein_id}_{drug_id}_{pmc_id}.html")
                        with open(save_file_path, "w", encoding="utf-8") as S:
                            S.write(pmc_content)

                        # check if found by fuzzy match or exact match
                        found_by_fuzzy = False
                        found_by_exact = False
                        if len(fuzzy_match_protein) > 0 and len(fuzzy_match_drug) > 0:
                            found_by_fuzzy = True
                        if len(exact_match_protein) > 0 and len(exact_match_drug) > 0:
                            found_by_exact = True

                        if found_by_fuzzy and found_by_exact:
                            fuzzy_agrees_exact += 1

                        if found_by_fuzzy and not found_by_exact:
                            fuzzy_no_exact += 1

                        if found_by_exact and not found_by_fuzzy:
                            exact_no_fuzzy += 1

                        metadata.append({
                            "PMC": pmc_id,
                            "PMCtitle": query["Title"],
                            "PMCabstract": query["Abstract"], 
                            "Query_Protein": protein_id,
                            "Query_Drug": drug_id,
                            "ProteinNames": found_proteins,
                            "DrugNames": found_drugs,
                            "FuzzyMatchProtein": fuzzy_match_protein,
                            "FuzzyMatchDrug": fuzzy_match_drug,
                            "ExactMatchProtein": exact_match_protein,
                            "ExactMatchDrug": exact_match_drug,
                        })

            ctr += 1
            print(f"Processed {ctr} queries, found {i} matches")

    metadata_df = pd.DataFrame(metadata)
    metadata_df.to_csv(os.path.join(save_dir, "metadata90.csv"), index=False)

    # print(f"Fuzzy match and exact match: {fuzzy_agrees_exact}")
    # print(f"Fuzzy match but no exact match: {fuzzy_no_exact}")
    # print(f"Exact match but no fuzzy match: {exact_no_fuzzy}")

    # # print these stats as a percentage of the total number of matches
    # total_matches = fuzzy_agrees_exact + fuzzy_no_exact + exact_no_fuzzy
    # print(f"Fuzzy match and exact match: {fuzzy_agrees_exact/total_matches}")
    # print(f"Fuzzy match but no exact match: {fuzzy_no_exact/total_matches}")
    # print(f"Exact match but no fuzzy match: {exact_no_fuzzy/total_matches}")

    # # plot the stats
    # stats = [fuzzy_agrees_exact, fuzzy_no_exact, exact_no_fuzzy]
    # labels = ["Fuzzy match and exact match", "Fuzzy match but no exact match", "Exact match but no fuzzy match"]

    # plt.pie(stats, labels=labels, autopct='%1.1f%%')

    # plt.savefig(os.path.join(save_dir, "match_stats.png"))
    # plt.show()

def pubchem_id_to_name(drug):
    x = pubchem_ids[drug]
    # get first val in x
    return x[list(x.keys())[0]]

def deduplicate_papers(dir):
    # load metadata
    data = pd.read_csv(os.path.join(dir, "metadata90.csv"))
    # create cols not present in the original metadata and fill with 'NA'
    data['ProteinMatch'] = 'NA'
    data['DrugMatch'] = 'NA'
    grouped_data = data.groupby('PMC').agg({
        'PMCtitle': 'first',
        'PMCabstract': lambda x: ' '.join(x.dropna().unique()),
        'Query_Protein': 'first',
        'Query_Drug': 'first',
        'ProteinNames': lambda x: list(set().union(*x.apply(eval))),
        'DrugNames': lambda x: list(set().union(*x.apply(eval))),
        'FuzzyMatchProtein': lambda x: list(set().union(*x.apply(eval))),
        'FuzzyMatchDrug': lambda x: list(set().union(*x.apply(eval))),
        'ExactMatchProtein': lambda x: list(set().union(*x.apply(eval))),
        'ExactMatchDrug': lambda x: list(set().union(*x.apply(eval))),
        'DrugMatch': lambda x: ', '.join(x.unique()),
        'ProteinMatch': lambda x: ', '.join(x.unique())
    }).reset_index()
    # fill in drug pubchem ids
    grouped_data['CID'] = grouped_data['Query_Drug'].apply(pubchem_id_to_name)

    grouped_data.to_csv(os.path.join(dir, "deduplicated_metadata90.csv"), index=False)


if __name__ == "__main__":
    filter_papers("filtered_papers_final")
    deduplicate_papers("filtered_papers_final")
 