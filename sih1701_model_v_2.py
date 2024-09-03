# -*- coding: utf-8 -*-
"""SIH1701-Model-v.2.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1J9-dyXjldx0b94rDReGGeNo6PAnNnvdS
"""

!pip install langchain   faiss-cpu  transformers torch pdfplumber

!pip install langchain_community

from langchain.vectorstores import FAISS
from langchain.docstore.document import Document
import faiss
import numpy as np
import torch
from transformers import BertModel, BertTokenizer
import pdfplumber
import re

# Define the section headers to split on
SECTION_HEADERS = [
    "PETITIONER:",
    "RESPONDENT:",
    "DATE OF JUDGMENT:",
    "BENCH:",
    "CITATION:",
    "ACT:",
    "HEADNOTE:",
    "JUDGMENT:"
]

# Function to split text based on section headers
def split_text_by_sections(text):
    # Create a regular expression pattern to match section headers
    pattern = '|'.join(re.escape(header) for header in SECTION_HEADERS)
    sections = re.split(pattern, text, flags=re.IGNORECASE)
    return [section.strip() for section in sections if section.strip()]

# Updated pdf_loader function to split text by sections
def pdf_loader(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text()
    sections = split_text_by_sections(text)
    return {section_header: Document(page_content=section)
            for section_header, section in zip(SECTION_HEADERS, sections)}

# Initialize the BERT model and tokenizer
tokenizer = BertTokenizer.from_pretrained('nlpaueb/legal-bert-base-uncased')
model = BertModel.from_pretrained('nlpaueb/legal-bert-base-uncased')

def get_embeddings(texts):
    inputs = tokenizer(texts, return_tensors='pt', padding=True, truncation=True)
    with torch.no_grad():
        outputs = model(**inputs)
    embeddings = outputs.last_hidden_state.mean(dim=1).numpy()
    return embeddings

class FAISSVectorStore(FAISS):
    def __init__(self, index, documents):
        self.index = index
        self.docstore = {i: doc for i, doc in enumerate(documents)}
        self.index_to_docstore_id = {i: i for i in range(len(documents))}

    def search(self, query_embeddings, k=5):
        distances, indices = self.index.search(query_embeddings, k)
        results = [(distances[i], [self.docstore[idx] for idx in indices[i]]) for i in range(len(distances))]
        return results

# Function to calculate similarity between two sets of section embeddings
def calculate_similarity(embedding1, embedding2):
    faiss_index = faiss.IndexFlatL2(embedding1.shape[1])
    faiss_index.add(embedding2.astype(np.float32))
    distances, _ = faiss_index.search(embedding1.astype(np.float32), k=1)
    similarity = 1 / (1 + distances[0][0])  # Convert distance to similarity (0-1 scale)
    return similarity

# Function to search for similar PDFs and print the top 5 matches
def search_similar_pdfs(query_pdf_path):
    query_document = pdf_loader(query_pdf_path)
    pdf_similarities = []

    for stored_pdf in stored_pdf_sections:
        section_similarities = []
        for section_header in SECTION_HEADERS:
            if section_header in query_document and section_header in stored_pdf:
                query_embedding = get_embeddings([query_document[section_header].page_content])
                stored_embedding = stored_pdf[section_header]["embedding"]
                similarity = calculate_similarity(query_embedding, stored_embedding)
                section_similarities.append(similarity)

        # Average similarity for this stored PDF
        if section_similarities:
            avg_similarity = np.mean(section_similarities)
            pdf_similarities.append((avg_similarity, stored_pdf))

    # Rank PDFs based on similarity
    ranked_pdfs = sorted(pdf_similarities, key=lambda x: x[0], reverse=True)

    # Print ranked PDFs and their content
    for rank, (similarity, pdf_content) in enumerate(ranked_pdfs[:2], start=1):
        print(f"\nRank {rank}: Similarity {similarity:.4f}")
        for section_header, content in pdf_content.items():
            print(f"\nSection: {section_header}\nContent: {content['text'][:500]}...")  # Print first 500 chars of each section

def database_processing() :
  for pdf_file in pdf_files:
      document = pdf_loader(pdf_file)
      section_data = {}
      for section_header, doc in document.items():
          texts = [doc.page_content]
          embeddings = get_embeddings(texts)
          section_data[section_header] = {"text": texts, "embedding": embeddings}
      stored_pdf_sections.append(section_data)

# Store PDFs and generate their embeddings by sections
pdf_files = ["/content/-0___jonew__judis__10187.pdf", "/content/-0___jonew__judis__10220.pdf", "/content/-0___jonew__judis__10290.pdf"]
stored_pdf_sections = []
database_processing()

search_similar_pdfs("/content/-0___jonew__judis__10187.pdf")