import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

def calculate_interaction(path):
    df = pd.read_csv(path)
    
    drug_protein_interaction = {}

    for index, row in df.iterrows():
        drug = row['CID']
        protein = row['Query_Protein']
        if (drug, protein) not in drug_protein_interaction:
            drug_protein_interaction[(drug, protein)] = {
                'Upregulation': 0,
                'Downregulation': 0,
                'Neutral': 0,
                'Upregulation_count': 0,
                'Downregulation_count': 0,
                'Neutral_count': 0,
            }
        interaction = row['interaction_type']
        drug_protein_interaction[(drug, protein)][interaction] += row['expt_weight']
        if interaction == 'Upregulation':
            drug_protein_interaction[(drug, protein)]['Upregulation_count'] += 1
        elif interaction == 'Downregulation':
            drug_protein_interaction[(drug, protein)]['Downregulation_count'] += 1
        else:
            drug_protein_interaction[(drug, protein)]['Neutral_count'] += 1

    return drug_protein_interaction

def merge_scores(drug_protein_interaction):
    for key in drug_protein_interaction:
        interaction = drug_protein_interaction[key]
        # Calculate the final score
        interaction['final_score'] = interaction['Upregulation'] - interaction['Downregulation']
        
        if interaction['Neutral'] > interaction['Upregulation'] and interaction['Neutral'] > interaction['Downregulation']:
            interaction['final_score'] = 0
        
        if interaction['Upregulation'] == interaction['Downregulation'] and interaction['Upregulation'] > interaction['Neutral'] and interaction['Upregulation'] > 0:
            interaction['final_score'] = np.inf

    return drug_protein_interaction

def create_heatmap(drug_protein_interaction):
    # Convert the interaction dictionary to a DataFrame for easy manipulation
    data = {
        'Drug': [],
        'Protein': [],
        'Score': []
    }

    for (drug, protein), interaction in drug_protein_interaction.items():
        data['Drug'].append(drug)
        data['Protein'].append(protein)
        # Replace inf with a large number for visualization
        score = interaction['final_score']
        if score == np.inf:
            score = 1e10  # A very large number
        data['Score'].append(score)

    df_interactions = pd.DataFrame(data)

    # Pivot the data to create a matrix format for the heatmap
    heatmap_data = df_interactions.pivot(index='Protein', columns='Drug', values='Score')
    # Plot the heatmap
    plt.figure(figsize=(12, 8))
    sns.heatmap(heatmap_data, annot=True, cmap="coolwarm", cbar_kws={'label': 'Interaction Score'})
    plt.title("Drug-Protein Interaction Heatmap")
    plt.show()

def save_to_csv(interaction, path):
    data = {
        'Drug': [],
        'Protein': [],
        'Upregulation': [],
        'Downregulation': [],
        'Neutral': [],
        'Final Score': [],
        'Upregulation_count': [],
        'Downregulation_count': [],
        'Neutral_count': [],
    }

    for (drug, protein), interactions in interaction.items():
        data['Drug'].append(drug)
        data['Protein'].append(protein)
        data['Upregulation'].append(interactions['Upregulation'])
        data['Downregulation'].append(interactions['Downregulation'])
        data['Neutral'].append(interactions['Neutral'])
        data['Upregulation_count'].append(interactions['Upregulation_count'])
        data['Downregulation_count'].append(interactions['Downregulation_count'])
        data['Neutral_count'].append(interactions['Neutral_count']) 
        data['Final Score'].append(interactions['final_score'])

    df = pd.DataFrame(data)
    df.to_csv(path, index=False)


# Example usage
path = 'extracted_relations_few_shot.csv'
drug_protein_interaction = calculate_interaction(path)
# save it as a csv file
merged_interactions = merge_scores(drug_protein_interaction)
save_to_csv(merged_interactions, 'drug_protein_interaction_matrix_few_shot.csv')
create_heatmap(merged_interactions)


path = 'extracted_relations_Zero_shot.csv'
drug_protein_interaction = calculate_interaction(path)
df = pd.DataFrame(drug_protein_interaction)
# save it as a csv file
merged_interactions = merge_scores(drug_protein_interaction)
save_to_csv(merged_interactions, 'drug_protein_interaction_matrix_zero_shot.csv')
create_heatmap(merged_interactions)
