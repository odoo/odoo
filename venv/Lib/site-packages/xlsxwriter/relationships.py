###############################################################################
#
# Relationships - A class for writing the Excel XLSX Worksheet file.
#
# SPDX-License-Identifier: BSD-2-Clause
# Copyright 2013-2023, John McNamara, jmcnamara@cpan.org
#

# Package imports.
from . import xmlwriter

# Long namespace strings used in the class.
schema_root = "http://schemas.openxmlformats.org"
package_schema = schema_root + "/package/2006/relationships"
document_schema = schema_root + "/officeDocument/2006/relationships"


class Relationships(xmlwriter.XMLwriter):
    """
    A class for writing the Excel XLSX Relationships file.


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

        super(Relationships, self).__init__()

        self.relationships = []
        self.id = 1

    ###########################################################################
    #
    # Private API.
    #
    ###########################################################################

    def _assemble_xml_file(self):
        # Assemble and write the XML file.

        # Write the XML declaration.
        self._xml_declaration()

        self._write_relationships()

        # Close the file.
        self._xml_close()

    def _add_document_relationship(self, rel_type, target, target_mode=None):
        # Add container relationship to XLSX .rels xml files.
        rel_type = document_schema + rel_type

        self.relationships.append((rel_type, target, target_mode))

    def _add_package_relationship(self, rel_type, target):
        # Add container relationship to XLSX .rels xml files.
        rel_type = package_schema + rel_type

        self.relationships.append((rel_type, target, None))

    def _add_ms_package_relationship(self, rel_type, target):
        # Add container relationship to XLSX .rels xml files. Uses MS schema.
        schema = "http://schemas.microsoft.com/office/2006/relationships"
        rel_type = schema + rel_type

        self.relationships.append((rel_type, target, None))

    ###########################################################################
    #
    # XML methods.
    #
    ###########################################################################

    def _write_relationships(self):
        # Write the <Relationships> element.
        attributes = [
            (
                "xmlns",
                package_schema,
            )
        ]

        self._xml_start_tag("Relationships", attributes)

        for relationship in self.relationships:
            self._write_relationship(relationship)

        self._xml_end_tag("Relationships")

    def _write_relationship(self, relationship):
        # Write the <Relationship> element.
        rel_type, target, target_mode = relationship

        attributes = [
            ("Id", "rId" + str(self.id)),
            ("Type", rel_type),
            ("Target", target),
        ]

        self.id += 1

        if target_mode:
            attributes.append(("TargetMode", target_mode))

        self._xml_empty_tag("Relationship", attributes)
