###############################################################################
#
# Custom - A class for writing the Excel XLSX Custom Property file.
#
# Copyright 2013-2018, John McNamara, jmcnamara@cpan.org
#

# Package imports.
from . import xmlwriter


class Custom(xmlwriter.XMLwriter):
    """
    A class for writing the Excel XLSX Custom Workbook Property file.


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

        super(Custom, self).__init__()

        self.properties = []
        self.pid = 1

    def _set_properties(self, properties):
        # Set the document properties.
        self.properties = properties

    ###########################################################################
    #
    # Private API.
    #
    ###########################################################################

    def _assemble_xml_file(self):
        # Assemble and write the XML file.

        # Write the XML declaration.
        self._xml_declaration()

        self._write_properties()

        self._xml_end_tag('Properties')

        # Close the file.
        self._xml_close()

    ###########################################################################
    #
    # XML methods.
    #
    ###########################################################################

    def _write_properties(self):
        # Write the <Properties> element.
        schema = 'http://schemas.openxmlformats.org/officeDocument/2006/'
        xmlns = schema + 'custom-properties'
        xmlns_vt = schema + 'docPropsVTypes'

        attributes = [
            ('xmlns', xmlns),
            ('xmlns:vt', xmlns_vt),
        ]

        self._xml_start_tag('Properties', attributes)

        for custom_property in self.properties:
            # Write the property element.
            self._write_property(custom_property)

    def _write_property(self, custom_property):
        # Write the <property> element.

        fmtid = '{D5CDD505-2E9C-101B-9397-08002B2CF9AE}'

        name, value, property_type = custom_property
        self.pid += 1

        attributes = [
            ('fmtid', fmtid),
            ('pid', self.pid),
            ('name', name),
        ]

        self._xml_start_tag('property', attributes)

        if property_type == 'number_int':
            # Write the vt:i4 element.
            self._write_vt_i4(value)
        elif property_type == 'number':
            # Write the vt:r8 element.
            self._write_vt_r8(value)
        elif property_type == 'date':
            # Write the vt:filetime element.
            self._write_vt_filetime(value)
        elif property_type == 'bool':
            # Write the vt:bool element.
            self._write_vt_bool(value)
        else:
            # Write the vt:lpwstr element.
            self._write_vt_lpwstr(value)

        self._xml_end_tag('property')

    def _write_vt_lpwstr(self, value):
        # Write the <vt:lpwstr> element.
        self._xml_data_element('vt:lpwstr', value)

    def _write_vt_filetime(self, value):
        # Write the <vt:filetime> element.
        self._xml_data_element('vt:filetime', value)

    def _write_vt_i4(self, value):
        # Write the <vt:i4> element.
        self._xml_data_element('vt:i4', value)

    def _write_vt_r8(self, value):
        # Write the <vt:r8> element.
        self._xml_data_element('vt:r8', value)

    def _write_vt_bool(self, value):
        # Write the <vt:bool> element.

        if value:
            value = 'true'
        else:
            value = 'false'

        self._xml_data_element('vt:bool', value)
