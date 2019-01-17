import numpy as np
import pandas as pd
import pickle
from collections import defaultdict
import re

from bs4 import BeautifulSoup

import sys
import os


from keras.preprocessing.text import Tokenizer, text_to_word_sequence
from keras.preprocessing.sequence import pad_sequences
from keras.utils.np_utils import to_categorical

from keras.layers import Embedding
from keras.layers import Dense, Input, Flatten
from keras.layers import Conv1D, MaxPooling1D, Embedding, Merge, Dropout, LSTM, GRU, Bidirectional, TimeDistributed
from keras.models import Model

from keras import backend as K
from keras.engine.topology import Layer, InputSpec
from keras import initializers
from test_clean_text import clean_text
from AttentionLayer.AttentionLayer import AttLayer

from sklearn.preprocessing import LabelEncoder

import nltk
nltk.download('punkt')


dataset = pd.read_csv('/content/drive/My Drive/Machine Learning/Fake News/Evaluation/Evaluation/fake_or_real_news.csv')
print(dataset.shape)

texts=[]
texts=dataset['text']
label=dataset['label']

labelEncoder=LabelEncoder()
encoded_label=labelEncoder.fit_transform(label)
y=np.reshape(encoded_label,(-1,1))


#X_train,X_test,y_train,y_test=train_test_split(X,y,test_size=0.2)

training_size=int(0.8*dataset.shape[0])
print(dataset.shape[0],training_size)
data_train=dataset[:training_size]['text']
y_train=y[:training_size]
data_rest=dataset[training_size:]['text']
y_test=y[training_size:]


MAX_SENT_LENGTH = 100
MAX_SENTS = 20
MAX_NB_WORDS = 400000
EMBEDDING_DIM = 100
#VALIDATION_SPLIT = 0.2

from nltk import tokenize

reviews = []
labels = []
texts = []

for idx in range(data_train.shape[0]):
    text = data_train[idx]
    text = clean_text(text)
    texts.append(text)
    sentences = tokenize.sent_tokenize(text)
    reviews.append(sentences)

    labels.append(y_train[idx])

tokenizer = Tokenizer(num_words=MAX_NB_WORDS)
tokenizer.fit_on_texts(texts)

data = np.zeros((len(texts), MAX_SENTS, MAX_SENT_LENGTH), dtype='int32')

for i, sentences in enumerate(reviews):
    for j, sent in enumerate(sentences):
        if j < MAX_SENTS:
            wordTokens = text_to_word_sequence(sent)
            k = 0
            for _, word in enumerate(wordTokens):
                if k < MAX_SENT_LENGTH and tokenizer.word_index[word] < MAX_NB_WORDS:
                    data[i, j, k] = tokenizer.word_index[word]
                    k = k + 1

word_index = tokenizer.word_index
print('Total %s unique tokens.' % len(word_index))

labels =(np.asarray(labels))
print('Shape of data tensor:', data.shape)
print('Shape of label tensor:', labels.shape)


reviews_test = []
labels_test = []
texts_test = []
#print(data_rest[training_size+0])
for idx in range(data_rest.shape[0]):
    text = data_rest[training_size+idx]
    text = clean_text(text)
    texts_test.append(text)
    sentences = tokenize.sent_tokenize(text)
    reviews_test.append(sentences)

    labels_test.append(y_test[idx])
print(text)

data_test = np.zeros((len(texts_test), MAX_SENTS, MAX_SENT_LENGTH), dtype='int32')

for i, sentences in enumerate(reviews_test):
    for j, sent in enumerate(sentences):
        if j < MAX_SENTS:
            wordTokens = text_to_word_sequence(sent)
            k = 0
            for _, word in enumerate(wordTokens):
                if word not in tokenizer.word_index.keys():
                    continue
                if k < MAX_SENT_LENGTH and tokenizer.word_index[word] < MAX_NB_WORDS:
                    data_test[i, j, k] = tokenizer.word_index[word]
                    k = k + 1

labels_test = np.asarray(labels_test)
print('Shape of data_test tensor:', data_test.shape)
print('Shape of label_test tensor:', labels_test.shape)


x_train = data
y_train = labels


x_test=data_test
y_test=labels_test

print('Number of positive and negative News in training set')
print(y_train.sum(axis=0))



GLOVE_DIR = "."
embeddings_index = {}
f = open(os.path.join(GLOVE_DIR, '/content/drive/My Drive/Machine Learning/Fake News/Evaluation/Evaluation/glove.6B.100d.txt'),encoding='utf-8')
for line in f:
    values = line.split()
    word = values[0]
    coefs = np.asarray(values[1:], dtype='float32')
    embeddings_index[word] = coefs
f.close()



print('Total %s word vectors.' % len(embeddings_index))

embedding_matrix = np.random.random((len(word_index) + 1, EMBEDDING_DIM))
for word, i in word_index.items():
    embedding_vector = embeddings_index.get(word)
    if embedding_vector is not None:
        embedding_matrix[i] = embedding_vector


embedding_matrix = np.random.random((len(word_index) + 1, EMBEDDING_DIM))
for word, i in word_index.items():
    embedding_vector = embeddings_index.get(word)
    if embedding_vector is not None:
        embedding_matrix[i] = embedding_vector


embedding_layer = Embedding(len(word_index) + 1,
                            EMBEDDING_DIM,
                            weights=[embedding_matrix],
                            input_length=MAX_SENT_LENGTH,
                            trainable=False)




word_input = Input(shape=(MAX_SENT_LENGTH,), dtype='int32')
embedded_sequences = embedding_layer(word_input)


l_lstm = Bidirectional(GRU(100, return_sequences=True))(embedded_sequences)
l_att = AttLayer(100)(l_lstm)
wordEncoder = Model(word_input, l_att)

sentence_input = Input(shape=(MAX_SENTS, MAX_SENT_LENGTH), dtype='int32')
sentence_encoder = TimeDistributed(wordEncoder)(sentence_input)

l_lstm_sent = Bidirectional(GRU(100, return_sequences=True))(sentence_encoder)
l_att_sent = AttLayer(100)(l_lstm_sent)

preds = Dense(1, activation='sigmoid')(l_att_sent)

model_Att = Model(sentence_input, preds)
model_Att.summary()
'''from keras.utils.vis_utils import plot_model
plot_model(model_Att, to_file='Merged/model_plot.png', show_shapes=True, show_layer_names=True)'''
model_Att.compile(loss='binary_crossentropy',
              optimizer='adam',
              metrics=['acc'])
model_Att.fit(x_train, y_train, validation_data=(x_val, y_val),
          epochs=10, batch_size=128)


score=model_Att.evaluate(x_test,y_test,verbose=1)
print('acc: '+str(score[1]))

from sklearn.metrics import precision_recall_fscore_support,classification_report
y_pred=model_Att.predict(x_test)
#print(y_pred)
y2=[]
for q in y_pred:
  if(q[0]>0.5):
    y2.append(True)
  else:
    y2.append(False)
print('Classification report:\n',classification_report(y_test,y2))
#print('Classification report:\n',precision_recall_fscore_support(y_test,y_pred))
#print(y_pred)
















