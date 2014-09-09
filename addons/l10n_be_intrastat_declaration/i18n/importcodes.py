#!/usr/bin/python

import csv
import xml.etree.ElementTree as ET

# Some constants
infile_csv = 'nom-e-14.asc'
outfile_xml = "../data/report.intrastat.code.xml"

# Generate terms
root = ET.Element("openerp")
data = ET.SubElement(root, "data")
data.set("noupdate", "1")
rows = csv.reader(open(infile_csv, encoding='iso8859-15'), delimiter=';', quotechar='"')
for row in rows:
    record = ET.SubElement(data, "record")
    record.set("id", "l10n_be_intrastat_declaration.intrastat_category_2014_%s" % row[0].encode('utf-8').decode('utf-8'))
    record.set("model", "report.intrastat.code")
    field = ET.SubElement(record, "field")
    field.set("name", "name")
    field.text = row[0].encode('utf-8').decode('utf-8')
    field = ET.SubElement(record, "field")
    field.set("name", "description")
    field.text = row[1].encode('utf-8').decode('utf-8')

datas = u'<?xml version="1.0" encoding="UTF-8"?>%s' % ET.tostring(root).decode('utf-8')
with open(outfile_xml, "w") as codelist:
    codelist.write(datas)
    
