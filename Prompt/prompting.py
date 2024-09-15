import os
import json
from bs4 import BeautifulSoup
import fuzzywuzzy.fuzz
import tiktoken
from openai import OpenAI
import pandas as pd

GPT_MODEL = "gpt-4o"

api_key = "#"
# Initialize the OpenAI client
client = OpenAI(api_key=api_key)

# PMC ID, PMD Title, Targeting sentence(s) / paragraphs, Queried Protein Name, Queried Drug Name, Uniprot ID, Drug ID.

df = pd.read_csv("filtered_papers_final\deduplicated_metadata90.csv")

# Load protein and drug names dictionaries
with open('Folic Acid Metabolism PMC analysis/protein_names_dict.json', 'r') as file:
    protein_names_dict = json.load(file)

with open('Folic Acid Metabolism PMC analysis/FA_Metabolism_Drug.json', 'r') as file:
    drug_names_dict = json.load(file)

tokenizer = tiktoken.encoding_for_model("gpt-4")

def truncate_text(text, max_tokens):
    tokens = tokenizer.encode(text)
    if len(tokens) > max_tokens:
        tokens = tokens[:max_tokens]
    return tokenizer.decode(tokens)

def parse_paper(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        html_content = file.read()

    soup = BeautifulSoup(html_content, 'html.parser')
    text = soup.get_text(separator=' ', strip=True)
    return text

def store_extracted_relations(drug, protein, effect, targeted_sentences, cot_reason, interaction_type, context, expt_type, expt_weight):
    return {
        "chain_of_thought_reasoning": cot_reason,
        "drug": drug,       
        "protein": protein,
        "effect": effect,
        "targeted_sentences": targeted_sentences,
        "interaction_type": interaction_type, # must be one of the following: "Upregulation", "Downregulation", "Neutral"
        "context": context, # context of the health-care scenario in which the relation was extracted
        "expt_type": expt_type, # type of experiment conducted in the study
        "expt_weight": expt_weight # how much weight to give to the extracted relation in the final analysis depending on the experiment
    }

def run_conversation(prompt, max_output_tokens):
    messages = [{"role": "user", "content": prompt}]
    tools = [
        {
            "type": "function",
            "function": {
                "name": "store_extracted_relations",
                "description": "Stores extracted relations indicating the effects of studied drug on the proteins and the relationship clusters.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "chain_of_thought_reasoning": {"type": "string", "description": "Detailed reasoning for the chain of thought in the extraction process."},
                        "drug": {"type": "string", "description": "Name of the drug (Official/Scientific) studied in the paper."},
                        "protein": {"type": "string", "description": "Name of the protein (Official/Scientific) studied in the paper."},
                        "effect": {"type": "string", "description": "Detailed effect of the drug on the protein, using coherent scientific language."},
                        "targeted_sentences": {"type": "array", "items": {"type": "string"}, "description": "Targeted sentence or sentences from the document that contain the extracted relation."},
                        "interaction_type": {"type": "string", "description": "Type of interaction between the drug and protein. Must be one of the following: 'Upregulation', 'Downregulation', 'Neutral'."},
                        "context": {"type": "string", "description": "Context of the health-care scenario in which the relation was extracted."},
                        "expt_type": {"type": "array", "items": {"type": "string"}, "description": "Type of experiment conducted in the study. Must be one of the following: 'In Silico', 'In Vitro', 'Ex Vivo', 'In Vivo', 'In Clinical'."},
                        "expt_weight": {"type": "number", "description": "How much weight to give to the extracted relation in the final analysis depending on the experiment. Consider this rubric as a guideline:"+
                                        '''1 (In Silico): Use for purely computational studies or simulations.
2 (In Vitro): Assign to studies involving cell cultures or biochemical assays in controlled environments.
2.5 (Ex Vivo): Apply to experiments on tissues or organs outside the organism but directly taken from a living system.
3 (In Vivo): For studies conducted within a living organism, particularly animal studies.
5 (In Clinical): Reserved for clinical trials or studies involving human participants.'''}},
                    "required": ["chain_of_thought_reasoning", "drug", "protein", "effect", "targeted_sentences", "interaction_type"]
                },
            },
        }
    ]

    response = client.chat.completions.create(
        model=GPT_MODEL,
        messages=messages,
        tools=tools,
        tool_choice={"type": "function", "function": {"name": "store_extracted_relations"}},
        temperature=0
    )

    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls
    extracted_relations = []

    if tool_calls:
        available_functions = {"store_extracted_relations": store_extracted_relations}
        messages.append(response_message)

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_to_call = available_functions[function_name]
            function_args = json.loads(tool_call.function.arguments)
            function_response = function_to_call(
                cot_reason=function_args.get("chain_of_thought_reasoning"),
                drug=function_args.get("drug"),
                protein=function_args.get("protein"),
                effect=function_args.get("effect"),
                targeted_sentences=function_args.get("targeted_sentences"),
                interaction_type=function_args.get("interaction_type"),
                context=function_args.get("context"),
                expt_type=function_args.get("expt_type"),
                expt_weight=function_args.get("expt_weight")
            )

            extracted_relations.append(function_response)

    return extracted_relations

def build_prompt(paper_file, drug_synonyms, protein_synonyms):
    text = parse_paper(paper_file)
    drug_synonyms = ','.join(drug_synonyms)
    protein_synonyms = ','.join(protein_synonyms)
    prompt = (
        f"Extract relations indicating the effects of the given drug/drugs on protein from the document. "
        f"Use the scientific or official nomenclature for the drugs and protein names.\n###\n{text}\n###\n\n"
        f"The following drug synonyms: {drug_synonyms} and protein synonyms: {protein_synonyms} were detected in the document using fuzzy and regex matching, and are provided for your reference.\n"
        f"Extract the effects of the drug on the protein based on your expertise in biomedical research.\n"
        f"Also, give the targeted sentence or sentences from the document that contain the extracted relation.\n"
        f"Next, you must classify the interaction between the drug and protein as 'Upregulation', 'Downregulation', or 'Neutral' to describe the effect of the drug on the protein.\n"
        f"Upregulation: The drug increases the expression or activity of the protein.\n"
        f"Downregulation: The drug decreases the expression or activity of the protein.\n"
        f"Neutral: The drug has no effect on the expression or activity of the protein.\n"
        f"Then, extract the context of the health-care scenario in which the relation was extracted. This could include the disease, treatment, or other relevant information.\n"
        f"Provide the type of experiment conducted in the study. The study could be 'In Silico', 'In Vitro', 'Ex Vivo', 'In Vivo', or 'In Clinical'. Multiple types can be selected if applicable.\n"
        f"Finally, assign an experimental weight to the extracted relation based on the type of experiment conducted in the study. Use the following rubric:\n"
        f"1 (In Silico): Use for purely computational studies or simulations.\n"
        f"2 (In Vitro): Assign to studies involving cell cultures or biochemical assays in controlled environments.\n"
        f"2.5 (Ex Vivo): Apply to experiments on tissues or organs outside the organism but directly taken from a living system.\n"
        f"3 (In Vivo): For studies conducted within a living organism, particularly animal studies.\n"
        f"5 (In Clinical): Reserved for clinical trials or studies involving human participants.\n"
        f"BEFORE YOU BEGIN: Formulate the intermediate resoning steps, as a chain of thought, for the extraction process."
    )

    # get html file name without directory
    file_name = os.path.basename(paper_file)
    # remove extension
    file_name = os.path.splitext(file_name)[0]
    # split by underscore
    file_parts = file_name.split("_")

    paper_ID = file_parts[-1]

    return prompt, paper_ID

def build_prompt_few_shot(paper_file, drug_synonyms, protein_synonyms):
    text = parse_paper(paper_file)
    drug_synonyms = ','.join(drug_synonyms)
    protein_synonyms = ','.join(protein_synonyms)


    few_shot_examples = (
        "Example 1:\n"
        "Chain of Thought Reasoning: The document discusses the effects of a series of 1,4-naphthoquinone derivatives, specifically compound 5i, on A549 cells. The key protein involved in the study is EGFR (Epidermal Growth Factor Receptor). The document details how compound 5i induces autophagy in A549 cells by promoting the recycling of EGFR and signal transduction, leading to the activation of the EGFR signaling pathway. Additionally, the binding mode between compound 5i and EGFR was identified through molecular docking, showing specific interactions that influence the EGFR-associated pathway. The document also mentions that compound 5i significantly up-regulates the expression of p-Akt and down-regulates EGFR protein expression, which is distinct from the effects of gefitinib, a known EGFR inhibitor. This indicates that compound 5i has a unique mechanism of action on the EGFR pathway, promoting autophagy and potentially enhancing anti-tumor activity.\n"
        "Drug: 2-Amino-1,4-Naphthoquinone Derivatives (specifically compound 5i)\n"
        "Protein: EGFR (Epidermal Growth Factor Receptor)\n"
        "Effect: Compound 5i induces autophagy by promoting the recycling of EGFR and signal transduction, leading to the activation of the EGFR signaling pathway. It significantly up-regulates the expression of p-Akt and down-regulates EGFR protein expression, which is distinct from the effects of gefitinib.\n"
        "Targeted Sentences: ['Surprisingly, in the following preliminary biological experiments, we found that compound 5i induced autophagy by promoting the recycling of EGFR and signal transduction in the A549 cell, resulting in the activation of the EGFR signal pathway.', 'Interestingly, EGFR protein expression was down-regulated remarkably after treatment with 5i (10 Î¼M), which lower three times lower than the control group.', 'Hence, combined with the above results, we preliminarily suspect that compound 5i will induce autophagy by promoting EGFR recycling and signal transduction in A549 cells to activate the EGFR signaling pathway.']\n"
        "Interaction Type: Upregulation\n"
        "Context: Cancer treatment, specifically targeting non-small cell lung cancer (A549 cells), by inducing autophagy through the EGFR signaling pathway.\n"
        "Expt Type: In Vitro\n"
        "Expt Score: 3\n"
        
        "\n\nExample 2:\n"
        "Chain of Thought Reasoning: To extract the effects of the drug on the protein, I first identified the drug and protein names mentioned in the document. The document discusses novel imidazole derivatives (AA1â€“AA8) and their effects on p38 MAP kinase. I focused on the sections detailing the synthesis, characterization, and evaluation of these compounds, particularly their anti-inflammatory activity and p38 MAP kinase inhibitory activity. I noted the specific compound AA6, which showed significant p38 MAP kinase inhibitory activity. The targeted sentences were identified based on their explicit mention of the drug's effect on the protein.\n"
        "Drug: AA6\n"
        "Protein: p38 MAP kinase\n"
        "Effect: AA6 possesses considerable p38 kinase inhibitory anti-inflammatory activity with an IC50 value of 403.57 Â± 6.35 nM compared to the prototype drug adezmapimod (SB203580) with an IC50 value of 222.44 Â± 5.98 nM.\n"
        "Targeted Sentences: ['The compound AA6 possesses considerable p38 kinase inhibitory anti-inflammatory activity with an IC50 value of 403.57 Â± 6.35 nM compared to the prototype drug adezmapimod (SB203580) with an IC50 value of 222.44 Â± 5.98 nM.']\n"
        "Interaction Type: Downregulation\n"
        "Context: The study focuses on developing novel anti-inflammatory drugs targeting p38 MAP kinase, which is involved in various inflammatory diseases such as rheumatoid arthritis, inflammatory bowel disease, cardiovascular events, neurodegenerative conditions, cancer, and COVID-19."
        "Expt Type: In Vitro\n"
        "Expt Score: 2.5\n"
        )

    few_shot_examples = (
        "Example 1:\n"
        "Chain of Thought Reasoning: The document discusses the effects of a series of 1,4-naphthoquinone derivatives, specifically compound 5i, on A549 cells. The key protein involved in the study is EGFR (Epidermal Growth Factor Receptor). The document details how compound 5i induces autophagy in A549 cells by promoting the recycling of EGFR and signal transduction, leading to the activation of the EGFR signaling pathway. Additionally, the binding mode between compound 5i and EGFR was identified through molecular docking, showing specific interactions that influence the EGFR-associated pathway. The document also mentions that compound 5i significantly up-regulates the expression of p-Akt and down-regulates EGFR protein expression, which is distinct from the effects of gefitinib, a known EGFR inhibitor. This indicates that compound 5i has a unique mechanism of action on the EGFR pathway, promoting autophagy and potentially enhancing anti-tumor activity.\n"
        "Example 2:\n"
        "Chain of Thought Reasoning: To extract the effects of the drug on the protein, I first identified the drug and protein names mentioned in the document. The document discusses novel imidazole derivatives (AA1â€“AA8) and their effects on p38 MAP kinase. I focused on the sections detailing the synthesis, characterization, and evaluation of these compounds, particularly their anti-inflammatory activity and p38 MAP kinase inhibitory activity. I noted the specific compound AA6, which showed significant p38 MAP kinase inhibitory activity. The targeted sentences were identified based on their explicit mention of the drug's effect on the protein.\n"
    )

    prompt = (
        f"Extract relations indicating the effects of the given drug/drugs on protein from the document. "
        f"Use the scientific or official nomenclature for the drugs and protein names.\n###\n{text}\n###\n\n"
        f"The following drug synonyms: {drug_synonyms} and protein synonyms: {protein_synonyms} were detected in the document using fuzzy and regex matching, and are provided for your reference.\n"
        f"Extract the effects of the drug on the protein based on your expertise in biomedical research.\n"
        f"Also, give the targeted sentence or sentences from the document that contain the extracted relation.\n"
        f"Next, you must classify the interaction between the drug and protein as 'Upregulation', 'Downregulation', or 'Neutral' to describe the effect of the drug on the protein.\n"
        f"Upregulation: The drug increases the expression or activity of the protein.\n"
        f"Downregulation: The drug decreases the expression or activity of the protein.\n"
        f"Neutral: The drug has no effect on the expression or activity of the protein.\n"
        f"BEFORE YOU BEGIN: Formulate the reasoning, as a chain of thought, for the extraction process."
        f"Use the following examples to guide your chain-of-thought:\n\n{few_shot_examples}"
    )

    # get html file name without directory
    file_name = os.path.basename(paper_file)
    # remove extension
    file_name = os.path.splitext(file_name)[0]
    # split by underscore
    file_parts = file_name.split("_")

    paper_ID = file_parts[-1]

    return prompt, paper_ID

def query_df(pmc_id):
    # Query the dataframe for the given PMC ID and return the relevant row as dictionary
    row = df[df['PMC'] == pmc_id].to_dict(orient='records')
    return row[0] if row else None

def save_extracted_relations(extracted_relations, metadata_dict, csv_file):
    # Save the extracted relations along with the metadata to a CSV file
    # combine dicts
    final_dict = {**metadata_dict, **extracted_relations}
    print(final_dict)
    final_df = pd.DataFrame([final_dict])
    # if csv file exists, append to it else save as new file
    if os.path.exists(csv_file):
        final_df.to_csv(csv_file, mode='a', header=False, index=False)
    else:
        final_df.to_csv(csv_file, index=False)


def extract_and_save_relations(pmc, mode):
    # check if the PMC ID exists in the csv file
    csv_file = "extracted_relations_zero_shot.csv" if mode == "zero_shot" else "extracted_relations_few_shot.csv"
    if os.path.exists(csv_file):
        df = pd.read_csv(csv_file)
        if pmc in df['PMC'].values:
            print(f"PMC ID: {pmc} already exists in the CSV file.")
            return
    pmc_info = query_df(pmc)
    paper_file = f"filtered_papers\{pmc_info['Query_Protein']}_{pmc_info['Query_Drug']}_{pmc_info['PMC']}.html"
    protein_synonyms = protein_names_dict[pmc_info['Query_Protein']]
    drug_synonyms = drug_names_dict[pmc_info['Query_Drug']]
    if mode == "few_shot":
        prompt, paper_ID = build_prompt_few_shot(paper_file, drug_synonyms, protein_synonyms)
    else:
        prompt, paper_ID = build_prompt(paper_file, drug_synonyms, protein_synonyms)
    extraction = run_conversation(prompt, 500)
    extraction = extraction[0]
    if mode == "few_shot":
        save_extracted_relations(extraction, pmc_info, "extracted_relations_few_shot.csv")
    else:
        save_extracted_relations(extraction, pmc_info, "extracted_relations_zero_shot.csv")


if __name__ == "__main__":


# zero-shot extraction
    extract_and_save_relations("PMC10143525", "zero_shot")
    extract_and_save_relations("PMC10210024", "zero_shot")
    extract_and_save_relations("PMC10456557", "zero_shot")
    extract_and_save_relations("PMC10505742", "zero_shot")
    extract_and_save_relations("PMC10530627", "zero_shot")
    extract_and_save_relations("PMC10638910", "zero_shot")
    extract_and_save_relations("PMC10662458", "zero_shot")
    extract_and_save_relations("PMC10669250", "zero_shot")
    extract_and_save_relations("PMC10695158", "zero_shot")


    # few-shot extraction
    extract_and_save_relations("PMC10143525", "few_shot")
    extract_and_save_relations("PMC10210024", "few_shot")
    extract_and_save_relations("PMC10456557", "few_shot")
    extract_and_save_relations("PMC10505742", "few_shot")
    extract_and_save_relations("PMC10530627", "few_shot")
    extract_and_save_relations("PMC10638910", "few_shot")
    extract_and_save_relations("PMC10662458", "few_shot")
    extract_and_save_relations("PMC10669250", "few_shot")
    extract_and_save_relations("PMC10695158", "few_shot")
    
