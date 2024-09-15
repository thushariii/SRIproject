import pandas as pd

data = pd.read_csv('Grouped_Metadata_by_PMC.csv')

# Calculate total fuzzy and exact matches for both proteins and drugs
total_fuzzy_protein_matches = data['FuzzyMatchProtein'].apply(lambda x: len(eval(x))).sum()
total_exact_protein_matches = data['ExactMatchProtein'].apply(lambda x: len(eval(x))).sum()
total_fuzzy_drug_matches = data['FuzzyMatchDrug'].apply(lambda x: len(eval(x))).sum()
total_exact_drug_matches = data['ExactMatchDrug'].apply(lambda x: len(eval(x))).sum()

# Creating a dataframe to show these counts
total_matches_df = pd.DataFrame({
    'Type': ['Fuzzy Protein Matches', 'Exact Protein Matches', 'Fuzzy Drug Matches', 'Exact Drug Matches'],
    'Count': [total_fuzzy_protein_matches, total_exact_protein_matches, total_fuzzy_drug_matches, total_exact_drug_matches]
})

# Display the dataframe (assuming ace_tools is a custom module for display)
import ace_tools as tools
tools.display_dataframe_to_user(name="Total Matches", dataframe=total_matches_df)

# Display the total matches dataframe
print(total_matches_df)

# Group the data by PMC and accumulate relevant columns
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
    'ProteinMatch': lambda x: ', '.join(x.unique()),
    'DrugMatch': lambda x: ', '.join(x.unique())
}).reset_index()

# Display the grouped metadata dataframe
tools.display_dataframe_to_user(name="Grouped Metadata by PMC", dataframe=grouped_data)

# Display the head of the grouped data
print(grouped_data.head())
