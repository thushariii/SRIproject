from bs4 import BeautifulSoup

# extract text from HTML file
def extract_text_from_html(file):
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text()
    return text

def process_text(text):
    # remove extra spaces and newlines
    text = text.replace('\n', ' ')
    text = ' '.join(text.split())
    return text

def build_prompt(text):
    prompt = 'This is a scientific paper: \n' + text + '\n\n'
    prompt += 'You are an expert biomedical researcher. Please verify if the following generated text is correct according to the given paper.:\n'
    # for term in terms:
    #     prompt += f'- {term}\n'
    return prompt

def save_prompt(prompt, filename):
    # save in a text file
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(prompt)

# print(extract_text_from_html("filtered_papers90\O00206_Pterin_PMC7522988.html"))

if __name__ == "__main__":
    text = extract_text_from_html("filtered_papers\O00206_XA_PMC8351238.html")
    text = process_text(text)
    # terms = ['XA', 'O00206']
    prompt = build_prompt(text)
    save_prompt(prompt, 'prompt.txt')