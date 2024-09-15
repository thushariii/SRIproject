import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import matplotlib.colors as mcolors

def plot_interaction_heatmap(df, output_file):
    """
    This function takes a DataFrame with 'Query_Protein', 'CID', 'interaction_type' columns
    and generates a heatmap showing solid interaction scores, handling duplicates by averaging them.

    Arguments:
    df : pd.DataFrame - The input DataFrame with interaction data.
    """

    # Define the function to calculate solid scores (+1 for Upregulation, -1 for Downregulation, 0 for Neutral/Unclear)
    def calculate_score(interaction_str):
        print(interaction_str)
        interactions = interaction_str.split(', ')
        score = sum(1 if i == 'Upregulation' else -1 if i == 'Downregulation' else 0 for i in interactions)
        if score == 0 and 'Upregulation' in interactions and 'Downregulation' in interactions:
            print(score)
            return 2 # If both Upregulation and Downregulation are equally present, return 2, which is a special unresolvable case
        return 1 if score > 0 else -1 if score < 0 else 0

    # Applying the function to get the solid score
    df['solid_score'] = df['interaction_type'].apply(calculate_score)

    # Aggregate data by mean (or you can use sum, median, etc.)
    df = df.groupby(['Query_Protein', 'CID']).agg({'solid_score': 'sum'}).reset_index()

    # Create pivot table for heatmap, use keyword arguments
    solid_heatmap_data = df.pivot(index='Query_Protein', columns='CID', values='solid_score')

    # Create a custom color map
    cmap = mcolors.ListedColormap(['red', 'gray', 'blue', 'black'])
    bounds = [-1.5, -0.5, 0.5, 1.5, 2.5]
    norm = mcolors.BoundaryNorm(bounds, cmap.N)

    # Plotting the heatmap, making cells with no interaction (NaN) white
    plt.figure(figsize=(10, 8))
    sns.heatmap(solid_heatmap_data, annot=True, cmap=cmap, cbar=False, linewidths=.5, linecolor='black', norm=norm,
                mask=solid_heatmap_data.isnull())
    plt.title('Solid Interaction Score Heatmap')
    plt.xlabel('CID')
    plt.ylabel('Query Protein')

    # Adding a custom legend
    colors = {'Downregulation': 'blue', 'Neutral': 'gray', 'Upregulation': 'red', 'Unresolvable': 'black'}
    labels = list(colors.keys())
    handles = [plt.Rectangle((0,0),1,1, color=colors[label]) for label in labels]
    plt.legend(handles, labels, loc='upper right', bbox_to_anchor=(1, 1))
    plt.savefig(output_file)
    plt.show()

# Example usage:
# df = pd.read_csv('your_input_file.csv')
# plot_interaction_heatmap(df)

csv1 = "extracted_relations_Zero_shot.csv"
csv2 = "extracted_relations_few_shot.csv"

df1 = pd.read_csv(csv1)
df2 = pd.read_csv(csv2)

print("Zero Shot Method protein-Drug interactionHeatmap")
plot_interaction_heatmap(df2, "zero_shot_heatmap.png")

print("Few Shot Method protein-Drug interactionHeatmap")
plot_interaction_heatmap(df1, "few_shot_heatmap.png")
