import itertools
import random
import re
import string
import traceback
from collections import OrderedDict
# noinspection PyUnresolvedReferences
from datetime import date, datetime, timedelta
# noinspection PyUnresolvedReferences
from dateutil.relativedelta import relativedelta
# noinspection PyUnresolvedReferences
from fractions import Fraction
# noinspection PyUnresolvedReferences
from math import *
from time import gmtime, strftime
from functools import reduce
# noinspection PyUnresolvedReferences
import sublime
# noinspection PyUnresolvedReferences
import sublime_plugin
import time
import bs4
# from urllib.request import urlopen
import requests
import json

def print_in_panel(view, edit, text):
    panel = view.window().find_output_panel("dutch_tools_panel")
    if not panel:
        panel = view.window().create_output_panel("dutch_tools_panel")
        
    view.window().run_command('show_panel', {"panel": 'output.dutch_tools_panel'})

    panel.insert(edit, panel.size(), text + "\n")


def get_transcription(word):
    # html = urlopen("https://www.mijnwoordenboek.nl/vertaal/NL/EN/%s" % word)
    # content = html.read()
    r = requests.get("https://www.mijnwoordenboek.nl/vertaal/NL/EN/%s" % word)
    # print("Enconding: " + r.encoding)
    soup = bs4.BeautifulSoup(r.text, 'html.parser')
    tag = soup.find("td", class_="smallcaps", string=re.compile("Uitspraak.*"))

    # print("### TAG FOUND: %s" % tag)
    # print("### " + tag.next_sibling.contents[0])

    if tag and tag.next_sibling and tag.next_sibling.contents[0]:
        return tag.next_sibling.contents[0]
    else:
        return None


def insert_transcription(view, edit):
    word = ""
    selection = view.sel()

    if selection:
        for sel in selection:
            word = view.substr(sel)
            transcription = get_transcription(word)

            if transcription:
                print_in_panel(view, edit, "Word: '%s' Transcription: %s" % (word, transcription))
                line = view.line(sel)
                ending = view.substr(line.end() - 1)
                if ending != ';':
                    transcription = ";" + transcription
                view.insert(edit, line.end(), transcription)
            else:
                print_in_panel(view, edit, "No transcription found for: %s" % word)
                transcription = "N/A"
                line = view.line(sel)
                ending = view.substr(line.end() - 1)
                if ending != ';':
                    transcription = ";"
                view.insert(edit, line.end(), transcription)


        
def request(action, **params):
    return {'action': action, 'params': params, 'version': 6}


def invoke(action, **params):
    requestJson = json.dumps(request(action, **params)).encode('utf-8')
    r = requests.post("http://localhost:8765", requestJson)
    response = json.loads(r.text)
    if len(response) != 2:
        raise Exception('response has an unexpected number of fields')
    if 'error' not in response:
        raise Exception('response is missing required error field')
    if 'result' not in response:
        raise Exception('response is missing required result field')
    if response['error'] is not None:
        raise Exception(response['error'])
    return response['result']        


def prepare_note(view, edit, nl, en, ru, tags, tr):
    return {
            "deckName": "Dutch-Russian::Woorden::B1",
            "modelName": "Dutch",
            "fields": {
                "Nederlands": nl,
                "English": en,
                "Russian": ru,
                "Transcription": tr
            },
            "options": {
                "allowDuplicate": False,
                "duplicateScope": "deck",
                "duplicateScopeOptions": {
                    "deckName": "Dutch-Russian::Woorden::B1",
                    "checkChildren": False
                }
            },
            "tags": tags.split(' ')
        }

class GetTranscriptionCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        insert_transcription(self.view, edit)


class SendToAnkiCommand(sublime_plugin.TextCommand):

    def run(self, edit):

        def on_done(value):
            print(value)

        try:
            panel = self.view.window().find_output_panel("local_vars")
            selection = self.view.sel()
            if selection:
                for sel in selection:
                    line = self.view.line(sel)
                    # view.insert(edit, line.b, ";" + transcription)
                    fields = [s for s in self.view.substr(line).split(';') if s != '']
                    if len(fields) < 5:
                        print_in_panel(self.view, edit, "Not enough fields (%d) for %s" % (len(fields), fields))
                    else:
                        note = prepare_note(self.view, edit, fields[0], fields[3], fields[4], fields[1], fields[2])
                        result = invoke('addNote', note=note)
                        print_in_panel(self.view, edit, "Created note %s for %s" % (result, fields))

                        selection.clear()
                        selection.add(sublime.Region(line.end() + 1, line.end() + 1))
                    # print_in_panel(self.view, edit, str(t))
                    # self.view.show_popup_menu(fields, lambda v: on_done(fields[v]))

            # result = invoke('addNote', note=prepare_note(self.view, edit))
            # self.view.show_popup("<b>Result</b><br>" + str(result), sublime.HIDE_ON_MOUSE_MOVE_AWAY)
        except Exception as e:
             print_in_panel(self.view, edit, "*** Error:" + str(e))



class ShowHelpCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        self.view.show_popup("""
<h3>Help</h3>
-----------------<br>
F5: get transcription<br>
F11: send to Anki<br>
-----------------<br>
Fields order: <ul>
<li>Nederlands
<li>Tags (space separated)
<li>Transcription
<li>English
<li>Russian
</ul>
""", 0, -1, 500, 300)


# show_popup(content, <flags>, <location>, <max_width>, <max_height>, <on_navigate>, <on_hide>)