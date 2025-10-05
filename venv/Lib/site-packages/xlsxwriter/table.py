###############################################################################
#
# Table - A class for writing the Excel XLSX Worksheet file.
#
# SPDX-License-Identifier: BSD-2-Clause
# Copyright 2013-2021, John McNamara, jmcnamara@cpan.org
#

from . import xmlwriter


class Table(xmlwriter.XMLwriter):
    """
    A class for writing the Excel XLSX Table file.


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

        super(Table, self).__init__()

        self.properties = {}

    ###########################################################################
    #
    # Private API.
    #
    ###########################################################################

    def _assemble_xml_file(self):
        # Assemble and write the XML file.

        # Write the XML declaration.
        self._xml_declaration()

        # Write the table element.
        self._write_table()

        # Write the autoFilter element.
        self._write_auto_filter()

        # Write the tableColumns element.
        self._write_table_columns()

        # Write the tableStyleInfo element.
        self._write_table_style_info()

        # Close the table tag.
        self._xml_end_tag('table')

        # Close the file.
        self._xml_close()

    def _set_properties(self, properties):
        # Set the document properties.
        self.properties = properties

    ###########################################################################
    #
    # XML methods.
    #
    ###########################################################################

    def _write_table(self):
        # Write the <table> element.
        schema = 'http://schemas.openxmlformats.org/'
        xmlns = schema + 'spreadsheetml/2006/main'
        table_id = self.properties['id']
        name = self.properties['name']
        display_name = self.properties['name']
        ref = self.properties['range']
        totals_row_shown = self.properties['totals_row_shown']
        header_row_count = self.properties['header_row_count']

        attributes = [
            ('xmlns', xmlns),
            ('id', table_id),
            ('name', name),
            ('displayName', display_name),
            ('ref', ref),
        ]

        if not header_row_count:
            attributes.append(('headerRowCount', 0))

        if totals_row_shown:
            attributes.append(('totalsRowCount', 1))
        else:
            attributes.append(('totalsRowShown', 0))

        self._xml_start_tag('table', attributes)

    def _write_auto_filter(self):
        # Write the <autoFilter> element.
        autofilter = self.properties.get('autofilter', 0)

        if not autofilter:
            return

        attributes = [('ref', autofilter,)]

        self._xml_empty_tag('autoFilter', attributes)

    def _write_table_columns(self):
        # Write the <tableColumns> element.
        columns = self.properties['columns']

        count = len(columns)

        attributes = [('count', count)]

        self._xml_start_tag('tableColumns', attributes)

        for col_data in columns:
            # Write the tableColumn element.
            self._write_table_column(col_data)

        self._xml_end_tag('tableColumns')

    def _write_table_column(self, col_data):
        # Write the <tableColumn> element.
        attributes = [
            ('id', col_data['id']),
            ('name', col_data['name']),
        ]

        if col_data.get('total_string'):
            attributes.append(('totalsRowLabel', col_data['total_string']))
        elif col_data.get('total_function'):
            attributes.append(('totalsRowFunction',
                               col_data['total_function']))

        if 'format' in col_data and col_data['format'] is not None:
            attributes.append(('dataDxfId', col_data['format']))

        if col_data.get('formula'):
            self._xml_start_tag('tableColumn', attributes)

            # Write the calculatedColumnFormula element.
            self._write_calculated_column_formula(col_data['formula'])

            self._xml_end_tag('tableColumn')
        else:
            self._xml_empty_tag('tableColumn', attributes)

    def _write_table_style_info(self):
        # Write the <tableStyleInfo> element.
        props = self.properties
        attributes = []

        name = props['style']
        show_first_column = 0 + props['show_first_col']
        show_last_column = 0 + props['show_last_col']
        show_row_stripes = 0 + props['show_row_stripes']
        show_column_stripes = 0 + props['show_col_stripes']

        if name is not None and name != '' and name != 'None':
            attributes.append(('name', name))

        attributes.append(('showFirstColumn', show_first_column))
        attributes.append(('showLastColumn', show_last_column))
        attributes.append(('showRowStripes', show_row_stripes))
        attributes.append(('showColumnStripes', show_column_stripes))

        self._xml_empty_tag('tableStyleInfo', attributes)

    def _write_calculated_column_formula(self, formula):
        # Write the <calculatedColumnFormula> element.
        self._xml_data_element('calculatedColumnFormula', formula)
