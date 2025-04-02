import pandas as pd
import numpy as np
from pyvi import ViTokenizer, ViPosTagger
from vncorenlp import VnCoreNLP

# Sử dụng ViTokenizer và ViPosTagger để tokenize và gán tags từ ngữ pháp
def preprocess_vietnamese_text(text):
    tokenized = ViTokenizer.tokenize(text)
    pos_tagged = ViPosTagger.postagging(tokenized)
    return pos_tagged[0]

# Sử dụng VnCoreNLP để trích xuất các đặc trưng ngôn ngữ
def extract_linguistic_features(text):
    annotator = VnCoreNLP(address="http://localhost", port=9000)
    annotated_text = annotator.annotate(text)
    features = {
        'num_sentences': len(annotated_text.sentences),
        'num_tokens': len(annotated_text.tokens),
        'num_nouns': len([t for t in annotated_text.tokens if t.pos.startswith('N')]),
        'num_verbs': len([t for t in annotated_text.tokens if t.pos.startswith('V')]),
        'num_adjectives': len([t for t in annotated_text.tokens if t.pos.startswith('A')]),
        'num_adverbs': len([t for t in annotated_text.tokens if t.pos.startswith('R')])
    }
    return features

# Kết hợp các bước tiền xử lý và trích xuất đặc trưng
def preprocess_and_extract(text):
    tokenized_text = preprocess_vietnamese_text(text)
    linguistic_features = extract_linguistic_features(text)
    return tokenized_text, linguistic_features

# Ví dụ sử dụng
text = "Tôi rất thích món ăn này, nó thật ngon và bổ dưỡng!"
tokenized, features = preprocess_and_extract(text)
print(tokenized)
print(features)
