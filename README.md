# sublime-anki-tools

This SublimeText plugin adds new notes to Anki.

## Prerequisites
The AnkiConnect plugin (https://ankiweb.net/shared/info/2055492159) should be installed and Anki should be running

## Usage

1. Create a new file
2. Set file syntax to 'anki-tools'
3. Declare the following configuration in your file:

```
# deck:       <PUT YOUR FULL DECKNAME HERE>
# model:      <PUT YOUR CARD TYPE HERE>
# fields:     <ENUM CARD FIELDS, COMMA-SEPARATED>
# tags:       <NAME OF THE FIELD WITH TAGS>
# min-fields: <MIN REQUIRED NUMBER OF FIELDS, 2 BY DEFAULT>
```

4. Then write down your fields in CSV format, separated with semi-column
5. Press "F11" key to send currently selected line to Anki
