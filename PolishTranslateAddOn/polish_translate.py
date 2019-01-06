# PolishTranslate Anki Add-on v0.1
# Translates words into Polish & downloads pronunciation.
#
# Copyright (c) 2019 Marcin Dlugajczyk            dlugajczykmarcin@gmail.com
# https://github.com/mdlugajczyk/PolishTranslate  Licensed under GPL v2

import os
from anki.hooks import addHook
from aqt import mw
from aqt.utils import showInfo, tooltip
import requests
import json
from bs4 import BeautifulSoup

# Get your unique API key by signing up at http://www.dictionaryapi.com/
MERRIAM_WEBSTER_API_KEY = ""

# Index of field with the work to translate
WORD_FIELD = 0

# Index of field to insert definitions into
DEFINITION_FIELD = 1

# Index of field to insert pronunciations into
PRONUNCIATION_FIELD = 2

PRIMARY_SHORTCUT = "ctrl+alt+e"

def get_translations(word):
    """Returns a list of translations of the word."""
    translations = []
    html = requests.get('https://en.bab.la/dictionary/english-polish/' + word).text
    tree = BeautifulSoup(html, "html.parser")
    for node in tree.findAll('ul',class_='sense-group-results'):
        for translation in node.findAll('a'):
            if translation.get('href').startswith('/dictionary/polish-english'):
                translations.append((translation.get_text()))
    return '; '.join(translations)

def get_pronunciation_url(word):
    # https://dictionaryapi.com/info/faq-audio-image#collegiate
    # https://www.dictionaryapi.com/products/json#sec-2.prs
    try:
        url = 'https://www.dictionaryapi.com/api/v3/references/collegiate/json/' + word + '?key=' + MERRIAM_WEBSTER_API_KEY
        resp = requests.get(url)
        response = json.loads(resp.text)
        audio_key = response[0]['hwi']['prs'][0]['sound']['audio']
        wav_url = 'https://media.merriam-webster.com/soundc11/' + word[0] + '/' + audio_key + '.wav'
        return wav_url, response[0]['meta']['id']
    except Exception as e:
          showInfo(str(e))
          return None, None

def do_word(word):
    url, new_word = get_pronunciation_url(word)
    if not url or not new_word:
        return None, None, None
    translations = get_translations(new_word)
    return url, new_word, translations

def get_definition(editor):
    editor.saveNow(lambda: _get_definition(editor))

def _get_definition(editor):
    word = editor.note.fields[0].strip()
    wav_url, new_word, translation = do_word(word)  #get_preferred_valid_entries(editor, word)
    if not wav_url or not translation:
        showInfo("Failed to fetch wav file & translation")
    sound_file = editor.urlToFile(wav_url).strip()
    insert_into_field(editor, new_word, WORD_FIELD, overwrite=True)
    insert_into_field(editor, '[sound:' + sound_file + ']', PRONUNCIATION_FIELD)
    insert_into_field(editor, translation, DEFINITION_FIELD)
    editor.web.eval("focusField(%d);" % 0)

def insert_into_field(editor, text, field_id, overwrite=False):
    if len(editor.note.fields) < field_id:
        tooltip('PolishTranslate: Failed to insert {0} into into field {1} (0-indexed)'.format(text, field_id))
        return
    if overwrite:
        editor.note.fields[field_id] = text
    else:
        editor.note.fields[field_id] += text
    editor.loadNote()

def setup_buttons(buttons, editor):
    editor._links['get_definition'] = get_definition
    return buttons + [editor._addButton(os.path.join(os.path.dirname(__file__), "images", "icon16.png"),
                                        'get_definition', "translate word and get pronunciation")]

addHook("setupEditorButtons", setup_buttons)

if getattr(mw.addonManager, "getConfig", None):
    config = mw.addonManager.getConfig(__name__)
    if 'MERRIAM_WEBSTER_API_KEY' in config:
        MERRIAM_WEBSTER_API_KEY = config['MERRIAM_WEBSTER_API_KEY']
    else:
        showInfo("PolishTranslate: Missing Merriam Webster API KEY in configuration!")
