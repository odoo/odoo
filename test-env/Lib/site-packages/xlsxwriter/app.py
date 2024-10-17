###############################################################################
#
# App - A class for writing the Excel XLSX App file.
#
# Copyright 2013-2018, John McNamara, jmcnamara@cpan.org
#

# Package imports.
from . import xmlwriter


class App(xmlwriter.XMLwriter):
    """
    A class for writing the Excel XLSX App file.


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

        super(App, self).__init__()

        self.part_names = []
        self.heading_pairs = []
        self.properties = {}

    def _add_part_name(self, part_name):
        # Add the name of a workbook Part such as 'Sheet1' or 'Print_Titles'.
        self.part_names.append(part_name)

    def _add_heading_pair(self, heading_pair):
        # Add the name of a workbook Heading Pair such as 'Worksheets',
        # 'Charts' or 'Named Ranges'.

        # Ignore empty pairs such as chartsheets.
        if not heading_pair[1]:
            return

        self.heading_pairs.append(('lpstr', heading_pair[0]))
        self.heading_pairs.append(('i4', heading_pair[1]))

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
        self._write_application()
        self._write_doc_security()
        self._write_scale_crop()
        self._write_heading_pairs()
        self._write_titles_of_parts()
        self._write_manager()
        self._write_company()
        self._write_links_up_to_date()
        self._write_shared_doc()
        self._write_hyperlink_base()
        self._write_hyperlinks_changed()
        self._write_app_version()

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
        xmlns = schema + 'extended-properties'
        xmlns_vt = schema + 'docPropsVTypes'

        attributes = [
            ('xmlns', xmlns),
            ('xmlns:vt', xmlns_vt),
        ]

        self._xml_start_tag('Properties', attributes)

    def _write_application(self):
        # Write the <Application> element.
        self._xml_data_element('Application', 'Microsoft Excel')

    def _write_doc_security(self):
        # Write the <DocSecurity> element.
        self._xml_data_element('DocSecurity', '0')

    def _write_scale_crop(self):
        # Write the <ScaleCrop> element.
        self._xml_data_element('ScaleCrop', 'false')

    def _write_heading_pairs(self):
        # Write the <HeadingPairs> element.
        self._xml_start_tag('HeadingPairs')
        self._write_vt_vector('variant', self.heading_pairs)
        self._xml_end_tag('HeadingPairs')

    def _write_titles_of_parts(self):
        # Write the <TitlesOfParts> element.
        parts_data = []

        self._xml_start_tag('TitlesOfParts')

        for part_name in self.part_names:
            parts_data.append(('lpstr', part_name))

        self._write_vt_vector('lpstr', parts_data)

        self._xml_end_tag('TitlesOfParts')

    def _write_vt_vector(self, base_type, vector_data):
        # Write the <vt:vector> element.
        attributes = [
            ('size', len(vector_data)),
            ('baseType', base_type),
        ]

        self._xml_start_tag('vt:vector', attributes)

        for vt_data in vector_data:
            if base_type == 'variant':
                self._xml_start_tag('vt:variant')

            self._write_vt_data(vt_data)

            if base_type == 'variant':
                self._xml_end_tag('vt:variant')

        self._xml_end_tag('vt:vector')

    def _write_vt_data(self, vt_data):
        # Write the <vt:*> elements such as <vt:lpstr> and <vt:if>.
        self._xml_data_element("vt:%s" % vt_data[0], vt_data[1])

    def _write_company(self):
        company = self.properties.get('company', '')

        self._xml_data_element('Company', company)

    def _write_manager(self):
        # Write the <Manager> element.
        if 'manager' not in self.properties:
            return

        self._xml_data_element('Manager', self.properties['manager'])

    def _write_links_up_to_date(self):
        # Write the <LinksUpToDate> element.
        self._xml_data_element('LinksUpToDate', 'false')

    def _write_shared_doc(self):
        # Write the <SharedDoc> element.
        self._xml_data_element('SharedDoc', 'false')

    def _write_hyperlink_base(self):
        # Write the <HyperlinkBase> element.
        hyperlink_base = self.properties.get('hyperlink_base')

        if hyperlink_base is None:
            return

        self._xml_data_element('HyperlinkBase', hyperlink_base)

    def _write_hyperlinks_changed(self):
        # Write the <HyperlinksChanged> element.
        self._xml_data_element('HyperlinksChanged', 'false')

    def _write_app_version(self):
        # Write the <AppVersion> element.
        self._xml_data_element('AppVersion', '12.0000')
