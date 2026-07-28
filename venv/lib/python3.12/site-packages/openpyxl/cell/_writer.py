# Copyright (c) 2010-2023 openpyxl

from openpyxl.compat import safe_string
from openpyxl.xml.functions import Element, SubElement, whitespace, XML_NS, REL_NS
from openpyxl import LXML
from openpyxl.utils.datetime import to_excel, to_ISO8601
from datetime import timedelta

from openpyxl.worksheet.formula import DataTableFormula, ArrayFormula
from openpyxl.cell.rich_text import TextBlock

def _set_attributes(cell, styled=None):
    """
    Set coordinate and datatype
    """
    coordinate = cell.coordinate
    attrs = {'r': coordinate}
    if styled:
        attrs['s'] = f"{cell.style_id}"

    if cell.data_type == "s":
        attrs['t'] = "inlineStr"
    elif cell.data_type != 'f':
        attrs['t'] = cell.data_type

    value = cell._value

    if cell.data_type == "d":
        if hasattr(value, "tzinfo") and value.tzinfo is not None:
            raise TypeError("Excel does not support timezones in datetimes. "
                    "The tzinfo in the datetime/time object must be set to None.")

        if cell.parent.parent.iso_dates and not isinstance(value, timedelta):
            value = to_ISO8601(value)
        else:
            attrs['t'] = "n"
            value = to_excel(value, cell.parent.parent.epoch)

    if cell.hyperlink:
        cell.parent._hyperlinks.append(cell.hyperlink)

    return value, attrs


def etree_write_cell(xf, worksheet, cell, styled=None):

    value, attributes = _set_attributes(cell, styled)

    el = Element("c", attributes)
    if value is None or value == "":
        xf.write(el)
        return

    if cell.data_type == 'f':
        attrib = {}

        if isinstance(value, ArrayFormula):
            attrib = dict(value)
            value = value.text

        elif isinstance(value, DataTableFormula):
            attrib = dict(value)
            value = None

        formula = SubElement(el, 'f', attrib)
        if value is not None and not attrib.get('t') == "dataTable":
            formula.text = value[1:]
            value = None

    if cell.data_type == 's':
        inline_string = SubElement(el, 'is')
        if isinstance(value, str):
            text = SubElement(inline_string, 't')
            text.text = value
            whitespace(text)
        else:
            for r in value:
                se = SubElement(inline_string, 'r')
                if isinstance(r, TextBlock):
                    se2 = SubElement(se, 'rPr')
                    se2.append(r.font.to_tree())
                    text = r.name
                else:
                    text = r
                text = SubElement(se, 't')
                text.text = text
                whitespace(text)



    else:
        cell_content = SubElement(el, 'v')
        if value is not None:
            cell_content.text = safe_string(value)

    xf.write(el)


def lxml_write_cell(xf, worksheet, cell, styled=False):
    value, attributes = _set_attributes(cell, styled)

    if value == '' or value is None:
        with xf.element("c", attributes):
            return

    with xf.element('c', attributes):
        if cell.data_type == 'f':
            attrib = {}

            if isinstance(value, ArrayFormula):
                attrib = dict(value)
                value = value.text

            elif isinstance(value, DataTableFormula):
                attrib = dict(value)
                value = None

            with xf.element('f', attrib):
                if value is not None and not attrib.get('t') == "dataTable":
                    xf.write(value[1:])
                    value = None

        if cell.data_type == 's':
            with xf.element("is"):
                if isinstance(value, str):
                    attrs = {}
                    if value != value.strip():
                        attrs["{%s}space" % XML_NS] = "preserve"
                    el = Element("t", attrs) # lxml can't handle xml-ns
                    el.text = value
                    xf.write(el)
                    #with xf.element("t", attrs):
                        #xf.write(value)
                else:
                    for r in value:
                        with xf.element("r"):
                            if isinstance(r, TextBlock):
                                xf.write(r.font.to_tree(tagname='rPr'))
                                value = r.text
                            else:
                                value = r
                            attrs = {}
                            if value != value.strip():
                                attrs["{%s}space" % XML_NS] = "preserve"
                            el = Element("t", attrs) # lxml can't handle xml-ns
                            el.text = value
                            xf.write(el)

        else:
            with xf.element("v"):
                if value is not None:
                    xf.write(safe_string(value))


if LXML:
    write_cell = lxml_write_cell
else:
    write_cell = etree_write_cell
