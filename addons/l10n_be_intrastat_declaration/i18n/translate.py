#!/usr/bin/python

"""
Translates the interstat codes from English to Dutch, French and German.
The input files can be downloaded from the Nomenclature tab on
http://www.bnb.be/pub/stats/foreign/foreign.htm?l=en (substitute the desired
language for 'en' in the URL above). I transformed them to unicode and changed
the field delimiter to a comma, but the code can be trivially adapted to work
with the originals in ISO8859-15 with semicolon as field delimiter if you so
desire. Care must be taken to remove all translations that are not for the
report.intrastat.code model as OpenERP doesn't allow per-model translation
export (see comments below).

Trivial improvements: automatically download the files from the BNB site, work
with those. But this quick n' dirty script fulfils my needs, and I'm building
a report module, not an automated translation service.
"""

import csv
import polib
import shutil

# Some constants
infile_csv = 'nom-e-14_utf8.csv'
infile_po = 'l10n_be_intrastat_declaration.po'

# Translations
trans = {'nl': 'n',
         'de': 'd',
         'fr': 'f'}

# Generate terms
terms = {}
with open(infile_csv, 'rb') as infile:
    rows = csv.reader(infile, delimiter=',', quotechar='"')
    for row in rows:
        terms.update({row[1].decode('utf-8'): row[0]})

# Translate
for key, value in trans.iteritems():
    infile = 'nom-%s-14_utf8.csv' % (value,)
    outfile = '%s.po' % (key,)
    shutil.copyfile(infile_po, outfile)
    trans_src = polib.pofile(outfile, encoding='utf-8', wrapwidth=9001)  # *g*
    trans_terms = {}
    with open(infile, 'rb') as translations:
        rows = csv.reader(translations, delimiter=',', quotechar='"')
        for row in rows:
            trans_terms.update({row[0]: row[1].decode('utf-8')})
    for entry in trans_src:
        code = terms.get(entry.msgid)
        # This shouldn't happen (TM), but it helps to weed out the translations
        # OpenERP has exported that are not related to interstat codes.
        # Unfortunately, OpenERP doesn't have a per-model translation export
        # feature, and to make matters worse, doesn't have the common sense to
        # keep similar translations (same model) together, so this aids in
        # solving the needle in haystack problem.
        if not code:
            print entry.msgid
        # I could do a check here to see if the code is found
        # but I prefer to know when a translation doesn't exist,
        # so let it crash with a KeyError if necessary.
        entry.msgstr = trans_terms[code]
    trans_src.save()
