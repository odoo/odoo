###############################################################################
#
# Metadata - A class for writing the Excel XLSX Metadata file.
#
# SPDX-License-Identifier: BSD-2-Clause
# Copyright 2013-2023, John McNamara, jmcnamara@cpan.org
#

from . import xmlwriter


class Metadata(xmlwriter.XMLwriter):
    """
    A class for writing the Excel XLSX Metadata file.


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

        super(Metadata, self).__init__()

    ###########################################################################
    #
    # Private API.
    #
    ###########################################################################

    def _assemble_xml_file(self):
        # Assemble and write the XML file.

        # Write the XML declaration.
        self._xml_declaration()

        # Write the metadata element.
        self._write_metadata()

        # Write the metadataTypes element.
        self._write_metadata_types()

        # Write the futureMetadata element.
        self._write_future_metadata()

        # Write the cellMetadata element.
        self._write_cell_metadata()

        self._xml_end_tag("metadata")

        # Close the file.
        self._xml_close()

    ###########################################################################
    #
    # XML methods.
    #
    ###########################################################################

    def _write_metadata(self):
        # Write the <metadata> element.
        xmlns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
        schema = "http://schemas.microsoft.com/office"
        xmlns_xda = schema + "/spreadsheetml/2017/dynamicarray"

        attributes = [
            ("xmlns", xmlns),
            ("xmlns:xda", xmlns_xda),
        ]

        self._xml_start_tag("metadata", attributes)

    def _write_metadata_types(self):
        # Write the <metadataTypes> element.
        attributes = [("count", 1)]

        self._xml_start_tag("metadataTypes", attributes)

        # Write the metadataType element.
        self._write_metadata_type()

        self._xml_end_tag("metadataTypes")

    def _write_metadata_type(self):
        # Write the <metadataType> element.
        attributes = [
            ("name", "XLDAPR"),
            ("minSupportedVersion", 120000),
            ("copy", 1),
            ("pasteAll", 1),
            ("pasteValues", 1),
            ("merge", 1),
            ("splitFirst", 1),
            ("rowColShift", 1),
            ("clearFormats", 1),
            ("clearComments", 1),
            ("assign", 1),
            ("coerce", 1),
            ("cellMeta", 1),
        ]

        self._xml_empty_tag("metadataType", attributes)

    def _write_future_metadata(self):
        # Write the <futureMetadata> element.
        attributes = [
            ("name", "XLDAPR"),
            ("count", 1),
        ]

        self._xml_start_tag("futureMetadata", attributes)
        self._xml_start_tag("bk")
        self._xml_start_tag("extLst")

        # Write the ext element.
        self._write_ext()

        self._xml_end_tag("extLst")
        self._xml_end_tag("bk")
        self._xml_end_tag("futureMetadata")

    def _write_ext(self):
        # Write the <ext> element.
        attributes = [("uri", "{bdbb8cdc-fa1e-496e-a857-3c3f30c029c3}")]

        self._xml_start_tag("ext", attributes)

        # Write the xda:dynamicArrayProperties element.
        self._write_xda_dynamic_array_properties()

        self._xml_end_tag("ext")

    def _write_xda_dynamic_array_properties(self):
        # Write the <xda:dynamicArrayProperties> element.
        attributes = [
            ("fDynamic", 1),
            ("fCollapsed", 0),
        ]

        self._xml_empty_tag("xda:dynamicArrayProperties", attributes)

    def _write_cell_metadata(self):
        # Write the <cellMetadata> element.
        attributes = [("count", 1)]

        self._xml_start_tag("cellMetadata", attributes)
        self._xml_start_tag("bk")

        # Write the rc element.
        self._write_rc()

        self._xml_end_tag("bk")
        self._xml_end_tag("cellMetadata")

    def _write_rc(self):
        # Write the <rc> element.
        attributes = [
            ("t", 1),
            ("v", 0),
        ]

        self._xml_empty_tag("rc", attributes)
