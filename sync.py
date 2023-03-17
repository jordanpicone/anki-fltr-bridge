#!/usr/bin/env python
# coding: utf-8

# In[1]:


import json
import requests
import csv
import pandas as pd


# In[2]:h


def anki_request(action, **params):
    request_data = json.dumps({"action": action, "params": params, "version": 6})
    response = requests.post("http://localhost:8765", data=request_data)
    return json.loads(response.content)


def read_fltr_data():
    fltr_data = {}
    with open(fltr_vocab, "r", encoding="utf-8") as f:
        tsv_reader = csv.reader(f, delimiter="\t")
        for row in tsv_reader:
            word = {}
            word['TL'] = row[0]
            word['L1'] = row[1]
            word['Sentence'] = row[2]
            word['Lemma'] = row[3]
            if row[4] == '':
                word['fltr_ease'] = 1
            else:
                word['fltr_ease'] = int(row[4])
            word['Lowercase'] = row[5]
            if word['Lemma'] == '':
                word['Lemma'] = word['TL']
            fltr_data[word['TL']] = word
    return fltr_data


def read_anki_data():
    note_ids = anki_request("findNotes", query=f'deck:"{anki_deck}"')["result"]
    notes = anki_request("notesInfo", notes=note_ids)["result"]
    anki_vocab = {}
    for note in notes:
        word = {}
        word['TL'] = note['fields']['Front']['value']
        word['L1'] = note['fields']['Back']['value']
        word['Cards'] = note['cards']

        ease = anki_request("getEaseFactors", cards=word['Cards'])["result"]
        ease = (ease[0] + ease[1]) / 2
        word['anki_ease'] = ease

        # Change this so it only takes the interval of the card with TL on front
        intervals = anki_request("getIntervals", cards=word['Cards'])["result"]
        interval = (intervals[0] + intervals[1]) / 2
        word['interval'] = interval

        word['fltr_ease_updated'] = anki_interval_to_fltr_ease(interval)
        print(word['TL'])
        anki_vocab[word['TL']] = word
    return anki_vocab


def anki_interval_to_fltr_ease(interval):
    if interval < 21:  # Less than 3 weeks
        return 1
    elif interval < 42:  # Less than 6 weeks
        return 2
    elif interval < 84:  # Less than 12 weeks
        return 3
    elif interval < 168:  # Less than 24 weeks
        return 4
    else:  # 24 weeks or more
        return 5


def create_anki_note(front, back):
    note = {
        "deckName": 'German',
        "modelName": 'Basic',
        "fields": {
            "Front": front,
            "Back": back
        },
        "options": {
            "allowDuplicate": False
        },
        "tags": []
    }

    result = anki_request("addNote", note=note)
    if result is None:
        print(f"Failed to create note for '{front}'")
    else:
        print(f"Created note {result} for '{front}'")


def read_config(file_path):
    with open(file_path, 'r') as f:
        config = json.load(f)
    return config


config_file_path = 'config.json'
config = read_config(config_file_path)

anki_deck = config["anki_deck"]
fltr_vocab = config["fltr_vocab"]

# Read data
fltr_data = read_fltr_data()
anki_data = read_anki_data()

# Create dataframes
fltr_df = pd.DataFrame.from_dict(fltr_data)
fltr_df = fltr_df.transpose()
fltr_df.head()

anki_df = pd.DataFrame.from_dict(anki_data)
anki_df = anki_df.transpose()
anki_df.head()

combined_df = pd.merge(fltr_df, anki_df, left_on=['TL', 'L1'], right_on=['TL', 'L1'], how='left')

# Find new words
nan_cards_rows = combined_df[combined_df['Cards'].isna()]

for index, row in nan_cards_rows.iterrows():
    front = row['TL']
    back = row['L1']
    create_anki_note(front, back)

# Output
fltr_output = combined_df[['TL', 'L1', 'Sentence', 'Lemma', 'fltr_ease_updated', 'Lowercase']]
fltr_output.to_csv("C:/Users/Jordan/Documents/FLTR/TL_Words.csv", sep='\t', index=False, header=False, encoding='utf-8')