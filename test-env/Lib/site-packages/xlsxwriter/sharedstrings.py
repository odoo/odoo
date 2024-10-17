###############################################################################
#
# SharedStrings - A class for writing the Excel XLSX sharedStrings file.
#
# Copyright 2013-2018, John McNamara, jmcnamara@cpan.org
#

# Standard packages.
import re
import sys

# Package imports.
from . import xmlwriter


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
        self._xml_end_tag('sst')

        # Close the file.
        self._xml_close()

    ###########################################################################
    #
    # XML methods.
    #
    ###########################################################################

    def _write_sst(self):
        # Write the <sst> element.
        xmlns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'

        attributes = [
            ('xmlns', xmlns),
            ('count', self.string_table.count),
            ('uniqueCount', self.string_table.unique_count),
        ]

        self._xml_start_tag('sst', attributes)

    def _write_sst_strings(self):
        # Write the sst string elements.

        for string in (self.string_table._get_strings()):
            self._write_si(string)

    def _write_si(self, string):
        # Write the <si> element.
        attributes = []

        # Excel escapes control characters with _xHHHH_ and also escapes any
        # literal strings of that type by encoding the leading underscore.
        # So "\0" -> _x0000_ and "_x0000_" -> _x005F_x0000_.
        # The following substitutions deal with those cases.

        # Escape the escape.
        string = re.sub('(_x[0-9a-fA-F]{4}_)', r'_x005F\1', string)

        # Convert control character to the _xHHHH_ escape.
        string = re.sub(r'([\x00-\x08\x0B-\x1F])',
                        lambda match: "_x%04X_" %
                        ord(match.group(1)), string)

        # Escape Unicode non-characters FFFE and FFFF.
        if sys.version_info[0] == 2:
            non_char1 = unichr(0xFFFE)
            non_char2 = unichr(0xFFFF)
        else:
            non_char1 = "\uFFFE"
            non_char2 = "\uFFFF"

        string = re.sub(non_char1, '_xFFFE_', string)
        string = re.sub(non_char2, '_xFFFF_', string)

        # Add attribute to preserve leading or trailing whitespace.
        if re.search(r'^\s', string) or re.search(r'\s$', string):
            attributes.append(('xml:space', 'preserve'))

        # Write any rich strings without further tags.
        if re.search('^<r>', string) and re.search('</r>$', string):
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
        """" Get the index of the string in the Shared String table. """
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
        """" Get a shared string from the index. """
        return self.string_array[index]

    def _sort_string_data(self):
        """" Sort the shared string data and convert from dict to list. """
        self.string_array = sorted(self.string_table,
                                   key=self.string_table.__getitem__)
        self.string_table = {}

    def _get_strings(self):
        """" Return the sorted string list. """
        return self.string_array
