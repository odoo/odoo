###############################################################################
#
# XMLwriter - A base class for XlsxWriter classes.
#
# Used in conjunction with XlsxWriter.
#
# SPDX-License-Identifier: BSD-2-Clause
# Copyright 2013-2023, John McNamara, jmcnamara@cpan.org
#

# Standard packages.
import re
from io import StringIO


class XMLwriter(object):
    """
    Simple XML writer class.

    """

    def __init__(self):
        self.fh = None
        self.escapes = re.compile('["&<>\n]')
        self.internal_fh = False

    def _set_filehandle(self, filehandle):
        # Set the writer filehandle directly. Mainly for testing.
        self.fh = filehandle
        self.internal_fh = False

    def _set_xml_writer(self, filename):
        # Set the XML writer filehandle for the object.
        if isinstance(filename, StringIO):
            self.internal_fh = False
            self.fh = filename
        else:
            self.internal_fh = True
            self.fh = open(filename, "w", encoding="utf-8")

    def _xml_close(self):
        # Close the XML filehandle if we created it.
        if self.internal_fh:
            self.fh.close()

    def _xml_declaration(self):
        # Write the XML declaration.
        self.fh.write("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n""")

    def _xml_start_tag(self, tag, attributes=[]):
        # Write an XML start tag with optional attributes.
        for key, value in attributes:
            value = self._escape_attributes(value)
            tag += ' %s="%s"' % (key, value)

        self.fh.write("<%s>" % tag)

    def _xml_start_tag_unencoded(self, tag, attributes=[]):
        # Write an XML start tag with optional, unencoded, attributes.
        # This is a minor speed optimization for elements that don't
        # need encoding.
        for key, value in attributes:
            tag += ' %s="%s"' % (key, value)

        self.fh.write("<%s>" % tag)

    def _xml_end_tag(self, tag):
        # Write an XML end tag.
        self.fh.write("</%s>" % tag)

    def _xml_empty_tag(self, tag, attributes=[]):
        # Write an empty XML tag with optional attributes.
        for key, value in attributes:
            value = self._escape_attributes(value)
            tag += ' %s="%s"' % (key, value)

        self.fh.write("<%s/>" % tag)

    def _xml_empty_tag_unencoded(self, tag, attributes=[]):
        # Write an empty XML tag with optional, unencoded, attributes.
        # This is a minor speed optimization for elements that don't
        # need encoding.
        for key, value in attributes:
            tag += ' %s="%s"' % (key, value)

        self.fh.write("<%s/>" % tag)

    def _xml_data_element(self, tag, data, attributes=[]):
        # Write an XML element containing data with optional attributes.
        end_tag = tag

        for key, value in attributes:
            value = self._escape_attributes(value)
            tag += ' %s="%s"' % (key, value)

        data = self._escape_data(data)
        self.fh.write("<%s>%s</%s>" % (tag, data, end_tag))

    def _xml_string_element(self, index, attributes=[]):
        # Optimized tag writer for <c> cell string elements in the inner loop.
        attr = ""

        for key, value in attributes:
            value = self._escape_attributes(value)
            attr += ' %s="%s"' % (key, value)

        self.fh.write("""<c%s t="s"><v>%d</v></c>""" % (attr, index))

    def _xml_si_element(self, string, attributes=[]):
        # Optimized tag writer for shared strings <si> elements.
        attr = ""

        for key, value in attributes:
            value = self._escape_attributes(value)
            attr += ' %s="%s"' % (key, value)

        string = self._escape_data(string)

        self.fh.write("""<si><t%s>%s</t></si>""" % (attr, string))

    def _xml_rich_si_element(self, string):
        # Optimized tag writer for shared strings <si> rich string elements.

        self.fh.write("""<si>%s</si>""" % string)

    def _xml_number_element(self, number, attributes=[]):
        # Optimized tag writer for <c> cell number elements in the inner loop.
        attr = ""

        for key, value in attributes:
            value = self._escape_attributes(value)
            attr += ' %s="%s"' % (key, value)

        self.fh.write("""<c%s><v>%.16G</v></c>""" % (attr, number))

    def _xml_formula_element(self, formula, result, attributes=[]):
        # Optimized tag writer for <c> cell formula elements in the inner loop.
        attr = ""

        for key, value in attributes:
            value = self._escape_attributes(value)
            attr += ' %s="%s"' % (key, value)

        self.fh.write(
            """<c%s><f>%s</f><v>%s</v></c>"""
            % (attr, self._escape_data(formula), self._escape_data(result))
        )

    def _xml_inline_string(self, string, preserve, attributes=[]):
        # Optimized tag writer for inlineStr cell elements in the inner loop.
        attr = ""
        t_attr = ""

        # Set the <t> attribute to preserve whitespace.
        if preserve:
            t_attr = ' xml:space="preserve"'

        for key, value in attributes:
            value = self._escape_attributes(value)
            attr += ' %s="%s"' % (key, value)

        string = self._escape_data(string)

        self.fh.write(
            """<c%s t="inlineStr"><is><t%s>%s</t></is></c>""" % (attr, t_attr, string)
        )

    def _xml_rich_inline_string(self, string, attributes=[]):
        # Optimized tag writer for rich inlineStr in the inner loop.
        attr = ""

        for key, value in attributes:
            value = self._escape_attributes(value)
            attr += ' %s="%s"' % (key, value)

        self.fh.write("""<c%s t="inlineStr"><is>%s</is></c>""" % (attr, string))

    def _escape_attributes(self, attribute):
        # Escape XML characters in attributes.
        try:
            if not self.escapes.search(attribute):
                return attribute
        except TypeError:
            return attribute

        attribute = (
            attribute.replace("&", "&amp;")
            .replace('"', "&quot;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "&#xA;")
        )
        return attribute

    def _escape_data(self, data):
        # Escape XML characters in data sections of tags.  Note, this
        # is different from _escape_attributes() in that double quotes
        # are not escaped by Excel.
        try:
            if not self.escapes.search(data):
                return data
        except TypeError:
            return data

        data = data.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return data
