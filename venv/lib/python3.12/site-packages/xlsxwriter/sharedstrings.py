###############################################################################
#
# SharedStrings - A class for writing the Excel XLSX sharedStrings file.
#
# SPDX-License-Identifier: BSD-2-Clause
# Copyright 2013-2023, John McNamara, jmcnamara@cpan.org
#

# Standard packages.
import re

# Package imports.
from . import xmlwriter
from .utility import preserve_whitespace

# Compile performance critical regular expressions.
re_control_chars_1 = re.compile("(_x[0-9a-fA-F]{4}_)")
re_control_chars_2 = re.compile(r"([\x00-\x08\x0b-\x1f])")


class SharedStrings(xmlwriter.XMLwriter):
    """
    A class for writing the Excel XLSX sharedStrings file.

    """

    ###########################################################################
    #
    # Public API.
    #
    ###########################################################################

    def __init__(self):
        """
        Constructor.

        """

        super(SharedStrings, self).__init__()

        self.string_table = None

    ###########################################################################
    #
    # Private API.
    #
    ###########################################################################

    def _assemble_xml_file(self):
        # Assemble and write the XML file.

        # Write the XML declaration.
        self._xml_declaration()

        # Write the sst element.
        self._write_sst()

        # Write the sst strings.
        self._write_sst_strings()

        # Close the sst tag.
        self._xml_end_tag("sst")

        # Close the file.
        self._xml_close()

    ###########################################################################
    #
    # XML methods.
    #
    ###########################################################################

    def _write_sst(self):
        # Write the <sst> element.
        xmlns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"

        attributes = [
            ("xmlns", xmlns),
            ("count", self.string_table.count),
            ("uniqueCount", self.string_table.unique_count),
        ]

        self._xml_start_tag("sst", attributes)

    def _write_sst_strings(self):
        # Write the sst string elements.

        for string in self.string_table.string_array:
            self._write_si(string)

    def _write_si(self, string):
        # Write the <si> element.
        attributes = []

        # Excel escapes control characters with _xHHHH_ and also escapes any
        # literal strings of that type by encoding the leading underscore.
        # So "\0" -> _x0000_ and "_x0000_" -> _x005F_x0000_.
        # The following substitutions deal with those cases.

        # Escape the escape.
        string = re_control_chars_1.sub(r"_x005F\1", string)

        # Convert control character to the _xHHHH_ escape.
        string = re_control_chars_2.sub(
            lambda match: "_x%04X_" % ord(match.group(1)), string
        )

        # Escapes non characters in strings.
        string = string.replace("\uFFFE", "_xFFFE_")
        string = string.replace("\uFFFF", "_xFFFF_")

        # Add attribute to preserve leading or trailing whitespace.
        if preserve_whitespace(string):
            attributes.append(("xml:space", "preserve"))

        # Write any rich strings without further tags.
        if string.startswith("<r>") and string.endswith("</r>"):
            self._xml_rich_si_element(string)
        else:
            self._xml_si_element(string, attributes)


# A metadata class to store Excel strings between worksheets.
class SharedStringTable(object):
    """
    A class to track Excel shared strings between worksheets.

    """

    def __init__(self):
        self.count = 0
        self.unique_count = 0
        self.string_table = {}
        self.string_array = []

    def _get_shared_string_index(self, string):
        """ " Get the index of the string in the Shared String table."""
        if string not in self.string_table:
            # String isn't already stored in the table so add it.
            index = self.unique_count
            self.string_table[string] = index
            self.count += 1
            self.unique_count += 1
            return index
        else:
            # String exists in the table.
            index = self.string_table[string]
            self.count += 1
            return index

    def _get_shared_string(self, index):
        """ " Get a shared string from the index."""
        return self.string_array[index]

    def _sort_string_data(self):
        """ " Sort the shared string data and convert from dict to list."""
        self.string_array = sorted(self.string_table, key=self.string_table.__getitem__)
        self.string_table = {}
