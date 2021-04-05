import json
import re

import bs4
import requests
import sublime
import sublime_plugin


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
    request_json = json.dumps(request(action, **params)).encode('utf-8')
    r = requests.post("http://localhost:8765", request_json)
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


def get_config(view, edit):

    def extract_config(s):
        m = re.match("^\s*#\s*(\w+)\s*[:=]\s*(.*)$", s)
        if m:
            return m.group(1), m.group(2)

    lines = view.find_all("^\s*#\s*\w+\s*[:=]\s*.*$")
    return dict([extract_config(view.substr(line)) for line in lines])


def prepare_note(fields, config):
    def get_field(idx, name):
        if idx < len(fields):
            return name, fields[idx]
        else:
            return name, ''

    def get_tags_list():
        if tags_field_name in fields_dict:
            tags_value = fields_dict.get(tags_field_name)
            if tags_value:
                return re.split("[, ]", tags_value)
            else:
                return []

    if 'deck' not in config:
        raise Exception("No 'deck' configuration found")
    if 'model' not in config:
        raise Exception("No 'model' configuration found")
    if 'fields' not in config:
        raise Exception("No 'fields' configuration found")

    fields_order = re.split("[;, :]", config['fields'])
    fields_dict = dict([get_field(idx, name) for idx, name in enumerate(fields_order)])

    tags_field_name = config.get('tags', 'Tags')
    tags_list = get_tags_list()

    if tags_field_name in fields_dict:
        del fields_dict[tags_field_name]

    return {
        "deckName": config['deck'],
        "modelName": config['model'],
        "fields": fields_dict,
        "options": {
            "allowDuplicate": False,
            "duplicateScope": "deck",
            "duplicateScopeOptions": {
                "deckName": config['deck'],
                "checkChildren": False
            }
        },
        "tags": tags_list
    }


class GetTranscriptionCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        insert_transcription(self.view, edit)


class SendToAnkiCommand(sublime_plugin.TextCommand):

    def run(self, edit):

        config = get_config(self.view, edit)

        try:
            panel = self.view.window().find_output_panel("local_vars")
            selection = self.view.sel()
            if selection:
                for sel in selection:
                    line = self.view.line(sel)
                    # view.insert(edit, line.b, ";" + transcription)
                    fields = [s for s in self.view.substr(line).split(';') if s != '']
                    min_fields = int(config.get('min-fields', 2))

                    if len(fields) < min_fields:
                        print_in_panel(self.view, edit, "Not enough fields (%d) for %s" % (len(fields), fields))
                    else:
                        note = prepare_note(fields, config)
                        print("Sending note: %s" % note)
                        result = invoke('addNote', note=note)
                        print_in_panel(self.view, edit, "Created note %s for %s" % (result, fields))

                        selection.clear()
                        selection.add(sublime.Region(line.end() + 1, line.end() + 1))
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
