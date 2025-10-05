###############################################################################
#
# ContentTypes - A class for writing the Excel XLSX ContentTypes file.
#
# SPDX-License-Identifier: BSD-2-Clause
# Copyright 2013-2021, John McNamara, jmcnamara@cpan.org
#

import copy
from . import xmlwriter

# Long namespace strings used in the class.
app_package = 'application/vnd.openxmlformats-package.'
app_document = 'application/vnd.openxmlformats-officedocument.'

defaults = [
    ['rels', app_package + 'relationships+xml'],
    ['xml', 'application/xml'],
]

overrides = [
    ['/docProps/app.xml', app_document + 'extended-properties+xml'],
    ['/docProps/core.xml', app_package + 'core-properties+xml'],
    ['/xl/styles.xml', app_document + 'spreadsheetml.styles+xml'],
    ['/xl/theme/theme1.xml', app_document + 'theme+xml'],
    ['/xl/workbook.xml', app_document + 'spreadsheetml.sheet.main+xml'],
]


class ContentTypes(xmlwriter.XMLwriter):
    """
    A class for writing the Excel XLSX ContentTypes file.


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

        super(ContentTypes, self).__init__()

        # Copy the defaults in case we need to change them.
        self.defaults = copy.deepcopy(defaults)
        self.overrides = copy.deepcopy(overrides)

    ###########################################################################
    #
    # Private API.
    #
    ###########################################################################

    def _assemble_xml_file(self):
        # Assemble and write the XML file.

        # Write the XML declaration.
        self._xml_declaration()

        self._write_types()
        self._write_defaults()
        self._write_overrides()

        self._xml_end_tag('Types')

        # Close the file.
        self._xml_close()

    def _add_default(self, default):
        # Add elements to the ContentTypes defaults.
        self.defaults.append(default)

    def _add_override(self, override):
        # Add elements to the ContentTypes overrides.
        self.overrides.append(override)

    def _add_worksheet_name(self, worksheet_name):
        # Add the name of a worksheet to the ContentTypes overrides.
        worksheet_name = "/xl/worksheets/" + worksheet_name + ".xml"

        self._add_override((worksheet_name,
                           app_document + 'spreadsheetml.worksheet+xml'))

    def _add_chartsheet_name(self, chartsheet_name):
        # Add the name of a chartsheet to the ContentTypes overrides.
        chartsheet_name = "/xl/chartsheets/" + chartsheet_name + ".xml"

        self._add_override((chartsheet_name,
                           app_document + 'spreadsheetml.chartsheet+xml'))

    def _add_chart_name(self, chart_name):
        # Add the name of a chart to the ContentTypes overrides.
        chart_name = "/xl/charts/" + chart_name + ".xml"

        self._add_override((chart_name, app_document + 'drawingml.chart+xml'))

    def _add_drawing_name(self, drawing_name):
        # Add the name of a drawing to the ContentTypes overrides.
        drawing_name = "/xl/drawings/" + drawing_name + ".xml"

        self._add_override((drawing_name, app_document + 'drawing+xml'))

    def _add_vml_name(self):
        # Add the name of a VML drawing to the ContentTypes defaults.
        self._add_default(('vml', app_document + 'vmlDrawing'))

    def _add_comment_name(self, comment_name):
        # Add the name of a comment to the ContentTypes overrides.
        comment_name = "/xl/" + comment_name + ".xml"

        self._add_override((comment_name,
                           app_document + 'spreadsheetml.comments+xml'))

    def _add_shared_strings(self):
        # Add the sharedStrings link to the ContentTypes overrides.
        self._add_override(('/xl/sharedStrings.xml',
                           app_document + 'spreadsheetml.sharedStrings+xml'))

    def _add_calc_chain(self):
        # Add the calcChain link to the ContentTypes overrides.
        self._add_override(('/xl/calcChain.xml',
                           app_document + 'spreadsheetml.calcChain+xml'))

    def _add_image_types(self, image_types):
        # Add the image default types.
        for image_type in image_types:
            extension = image_type

            if image_type in ('wmf', 'emf'):
                image_type = 'x-' + image_type

            self._add_default((extension, 'image/' + image_type))

    def _add_table_name(self, table_name):
        # Add the name of a table to the ContentTypes overrides.
        table_name = "/xl/tables/" + table_name + ".xml"

        self._add_override((table_name,
                           app_document + 'spreadsheetml.table+xml'))

    def _add_vba_project(self):
        # Add a vbaProject to the ContentTypes defaults.

        # Change the workbook.xml content-type from xlsx to xlsm.
        for i, override in enumerate(self.overrides):
            if override[0] == '/xl/workbook.xml':
                self.overrides[i][1] = 'application/vnd.ms-excel.' \
                    'sheet.macroEnabled.main+xml'

        self._add_default(('bin', 'application/vnd.ms-office.vbaProject'))

    def _add_custom_properties(self):
        # Add the custom properties to the ContentTypes overrides.
        self._add_override(('/docProps/custom.xml',
                           app_document + 'custom-properties+xml'))

    def _add_metadata(self):
        # Add the metadata file to the ContentTypes overrides.
        self._add_override(('/xl/metadata.xml',
                           app_document + 'spreadsheetml.sheetMetadata+xml'))

    ###########################################################################
    #
    # XML methods.
    #
    ###########################################################################

    def _write_defaults(self):
        # Write out all of the <Default> types.

        for extension, content_type in self.defaults:
            self._xml_empty_tag('Default',
                                [('Extension', extension),
                                 ('ContentType', content_type)])

    def _write_overrides(self):
        # Write out all of the <Override> types.
        for part_name, content_type in self.overrides:
            self._xml_empty_tag('Override',
                                [('PartName', part_name),
                                 ('ContentType', content_type)])

    def _write_types(self):
        # Write the <Types> element.
        xmlns = 'http://schemas.openxmlformats.org/package/2006/content-types'

        attributes = [('xmlns', xmlns,)]
        self._xml_start_tag('Types', attributes)

    def _write_default(self, extension, content_type):
        # Write the <Default> element.
        attributes = [
            ('Extension', extension),
            ('ContentType', content_type),
        ]

        self._xml_empty_tag('Default', attributes)

    def _write_override(self, part_name, content_type):
        # Write the <Override> element.
        attributes = [
            ('PartName', part_name),
            ('ContentType', content_type),
        ]

        self._xml_empty_tag('Override', attributes)
