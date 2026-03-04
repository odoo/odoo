###############################################################################
#
# Drawing - A class for writing the Excel XLSX Drawing file.
#
# SPDX-License-Identifier: BSD-2-Clause
# Copyright 2013-2023, John McNamara, jmcnamara@cpan.org
#

from . import xmlwriter
from .shape import Shape
from .utility import get_rgb_color


class Drawing(xmlwriter.XMLwriter):
    """
    A class for writing the Excel XLSX Drawing file.


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

        super(Drawing, self).__init__()

        self.drawings = []
        self.embedded = 0
        self.orientation = 0

    ###########################################################################
    #
    # Private API.
    #
    ###########################################################################

    def _assemble_xml_file(self):
        # Assemble and write the XML file.

        # Write the XML declaration.
        self._xml_declaration()

        # Write the xdr:wsDr element.
        self._write_drawing_workspace()

        if self.embedded:
            index = 0
            for drawing_properties in self.drawings:
                # Write the xdr:twoCellAnchor element.
                index += 1
                self._write_two_cell_anchor(index, drawing_properties)

        else:
            # Write the xdr:absoluteAnchor element.
            self._write_absolute_anchor(1)

        self._xml_end_tag("xdr:wsDr")

        # Close the file.
        self._xml_close()

    def _add_drawing_object(self):
        # Add a chart, image or shape sub object to the drawing.

        drawing_object = {
            "anchor_type": None,
            "dimensions": [],
            "width": 0,
            "height": 0,
            "shape": None,
            "anchor": None,
            "rel_index": 0,
            "url_rel_index": 0,
            "tip": None,
            "name": None,
            "description": None,
            "decorative": False,
        }

        self.drawings.append(drawing_object)

        return drawing_object

    ###########################################################################
    #
    # XML methods.
    #
    ###########################################################################

    def _write_drawing_workspace(self):
        # Write the <xdr:wsDr> element.
        schema = "http://schemas.openxmlformats.org/drawingml/"
        xmlns_xdr = schema + "2006/spreadsheetDrawing"
        xmlns_a = schema + "2006/main"

        attributes = [
            ("xmlns:xdr", xmlns_xdr),
            ("xmlns:a", xmlns_a),
        ]

        self._xml_start_tag("xdr:wsDr", attributes)

    def _write_two_cell_anchor(self, index, drawing_properties):
        # Write the <xdr:twoCellAnchor> element.
        anchor_type = drawing_properties["type"]
        dimensions = drawing_properties["dimensions"]
        col_from = dimensions[0]
        row_from = dimensions[1]
        col_from_offset = dimensions[2]
        row_from_offset = dimensions[3]
        col_to = dimensions[4]
        row_to = dimensions[5]
        col_to_offset = dimensions[6]
        row_to_offset = dimensions[7]
        col_absolute = dimensions[8]
        row_absolute = dimensions[9]
        width = drawing_properties["width"]
        height = drawing_properties["height"]
        shape = drawing_properties["shape"]
        anchor = drawing_properties["anchor"]
        rel_index = drawing_properties["rel_index"]
        url_rel_index = drawing_properties["url_rel_index"]
        tip = drawing_properties["tip"]
        name = drawing_properties["name"]
        description = drawing_properties["description"]
        decorative = drawing_properties["decorative"]

        attributes = []

        # Add attribute for positioning.
        if anchor == 2:
            attributes.append(("editAs", "oneCell"))
        elif anchor == 3:
            attributes.append(("editAs", "absolute"))

        # Add editAs attribute for shapes.
        if shape and shape.edit_as:
            attributes.append(("editAs", shape.edit_as))

        self._xml_start_tag("xdr:twoCellAnchor", attributes)

        # Write the xdr:from element.
        self._write_from(col_from, row_from, col_from_offset, row_from_offset)

        # Write the xdr:from element.
        self._write_to(col_to, row_to, col_to_offset, row_to_offset)

        if anchor_type == 1:
            # Graphic frame.
            # Write the xdr:graphicFrame element for charts.
            self._write_graphic_frame(index, rel_index, name, description, decorative)
        elif anchor_type == 2:
            # Write the xdr:pic element.
            self._write_pic(
                index,
                rel_index,
                col_absolute,
                row_absolute,
                width,
                height,
                shape,
                description,
                url_rel_index,
                tip,
                decorative,
            )
        else:
            # Write the xdr:sp element for shapes.
            self._write_sp(
                index,
                col_absolute,
                row_absolute,
                width,
                height,
                shape,
                description,
                url_rel_index,
                tip,
                decorative,
            )

        # Write the xdr:clientData element.
        self._write_client_data()

        self._xml_end_tag("xdr:twoCellAnchor")

    def _write_absolute_anchor(self, frame_index):
        self._xml_start_tag("xdr:absoluteAnchor")
        # Write the <xdr:absoluteAnchor> element.

        # Different coordinates for horizontal (= 0) and vertical (= 1).
        if self.orientation == 0:
            # Write the xdr:pos element.
            self._write_pos(0, 0)

            # Write the xdr:ext element.
            self._write_xdr_ext(9308969, 6078325)

        else:
            # Write the xdr:pos element.
            self._write_pos(0, -47625)

            # Write the xdr:ext element.
            self._write_xdr_ext(6162675, 6124575)

        # Write the xdr:graphicFrame element.
        self._write_graphic_frame(frame_index, frame_index)

        # Write the xdr:clientData element.
        self._write_client_data()

        self._xml_end_tag("xdr:absoluteAnchor")

    def _write_from(self, col, row, col_offset, row_offset):
        # Write the <xdr:from> element.
        self._xml_start_tag("xdr:from")

        # Write the xdr:col element.
        self._write_col(col)

        # Write the xdr:colOff element.
        self._write_col_off(col_offset)

        # Write the xdr:row element.
        self._write_row(row)

        # Write the xdr:rowOff element.
        self._write_row_off(row_offset)

        self._xml_end_tag("xdr:from")

    def _write_to(self, col, row, col_offset, row_offset):
        # Write the <xdr:to> element.
        self._xml_start_tag("xdr:to")

        # Write the xdr:col element.
        self._write_col(col)

        # Write the xdr:colOff element.
        self._write_col_off(col_offset)

        # Write the xdr:row element.
        self._write_row(row)

        # Write the xdr:rowOff element.
        self._write_row_off(row_offset)

        self._xml_end_tag("xdr:to")

    def _write_col(self, data):
        # Write the <xdr:col> element.
        self._xml_data_element("xdr:col", data)

    def _write_col_off(self, data):
        # Write the <xdr:colOff> element.
        self._xml_data_element("xdr:colOff", data)

    def _write_row(self, data):
        # Write the <xdr:row> element.
        self._xml_data_element("xdr:row", data)

    def _write_row_off(self, data):
        # Write the <xdr:rowOff> element.
        self._xml_data_element("xdr:rowOff", data)

    def _write_pos(self, x, y):
        # Write the <xdr:pos> element.

        attributes = [("x", x), ("y", y)]

        self._xml_empty_tag("xdr:pos", attributes)

    def _write_xdr_ext(self, cx, cy):
        # Write the <xdr:ext> element.

        attributes = [("cx", cx), ("cy", cy)]

        self._xml_empty_tag("xdr:ext", attributes)

    def _write_graphic_frame(
        self, index, rel_index, name=None, description=None, decorative=None
    ):
        # Write the <xdr:graphicFrame> element.
        attributes = [("macro", "")]

        self._xml_start_tag("xdr:graphicFrame", attributes)

        # Write the xdr:nvGraphicFramePr element.
        self._write_nv_graphic_frame_pr(index, name, description, decorative)

        # Write the xdr:xfrm element.
        self._write_xfrm()

        # Write the a:graphic element.
        self._write_atag_graphic(rel_index)

        self._xml_end_tag("xdr:graphicFrame")

    def _write_nv_graphic_frame_pr(self, index, name, description, decorative):
        # Write the <xdr:nvGraphicFramePr> element.

        if not name:
            name = "Chart " + str(index)

        self._xml_start_tag("xdr:nvGraphicFramePr")

        # Write the xdr:cNvPr element.
        self._write_c_nv_pr(index + 1, name, description, None, None, decorative)

        # Write the xdr:cNvGraphicFramePr element.
        self._write_c_nv_graphic_frame_pr()

        self._xml_end_tag("xdr:nvGraphicFramePr")

    def _write_c_nv_pr(self, index, name, description, url_rel_index, tip, decorative):
        # Write the <xdr:cNvPr> element.
        attributes = [("id", index), ("name", name)]

        # Add description attribute for images.
        if description and not decorative:
            attributes.append(("descr", description))

        if url_rel_index or decorative:
            self._xml_start_tag("xdr:cNvPr", attributes)

            if url_rel_index:
                self._write_a_hlink_click(url_rel_index, tip)

            if decorative:
                self._write_decorative()

            self._xml_end_tag("xdr:cNvPr")
        else:
            self._xml_empty_tag("xdr:cNvPr", attributes)

    def _write_decorative(self):
        self._xml_start_tag("a:extLst")

        self._write_uri_ext("{FF2B5EF4-FFF2-40B4-BE49-F238E27FC236}")
        self._write_a16_creation_id()
        self._xml_end_tag("a:ext")

        self._write_uri_ext("{C183D7F6-B498-43B3-948B-1728B52AA6E4}")
        self._write_adec_decorative()
        self._xml_end_tag("a:ext")

        self._xml_end_tag("a:extLst")

    def _write_uri_ext(self, uri):
        # Write the <a:ext> element.
        attributes = [("uri", uri)]

        self._xml_start_tag("a:ext", attributes)

    def _write_adec_decorative(self):
        # Write the <adec:decorative> element.
        xmlns = "http://schemas.microsoft.com/office/drawing/2017/decorative"
        val = "1"

        attributes = [
            ("xmlns:adec", xmlns),
            ("val", val),
        ]

        self._xml_empty_tag("adec:decorative", attributes)

    def _write_a16_creation_id(self):
        # Write the <a16:creationId> element.

        xmlns_a_16 = "http://schemas.microsoft.com/office/drawing/2014/main"
        creation_id = "{00000000-0008-0000-0000-000002000000}"

        attributes = [
            ("xmlns:a16", xmlns_a_16),
            ("id", creation_id),
        ]

        self._xml_empty_tag("a16:creationId", attributes)

    def _write_a_hlink_click(self, rel_index, tip):
        # Write the <a:hlinkClick> element.
        schema = "http://schemas.openxmlformats.org/officeDocument/"
        xmlns_r = schema + "2006/relationships"

        attributes = [
            ("xmlns:r", xmlns_r),
            ("r:id", "rId" + str(rel_index)),
        ]

        if tip:
            attributes.append(("tooltip", tip))

        self._xml_empty_tag("a:hlinkClick", attributes)

    def _write_c_nv_graphic_frame_pr(self):
        # Write the <xdr:cNvGraphicFramePr> element.
        if self.embedded:
            self._xml_empty_tag("xdr:cNvGraphicFramePr")
        else:
            self._xml_start_tag("xdr:cNvGraphicFramePr")

            # Write the a:graphicFrameLocks element.
            self._write_a_graphic_frame_locks()

            self._xml_end_tag("xdr:cNvGraphicFramePr")

    def _write_a_graphic_frame_locks(self):
        # Write the <a:graphicFrameLocks> element.
        attributes = [("noGrp", 1)]

        self._xml_empty_tag("a:graphicFrameLocks", attributes)

    def _write_xfrm(self):
        # Write the <xdr:xfrm> element.
        self._xml_start_tag("xdr:xfrm")

        # Write the xfrmOffset element.
        self._write_xfrm_offset()

        # Write the xfrmOffset element.
        self._write_xfrm_extension()

        self._xml_end_tag("xdr:xfrm")

    def _write_xfrm_offset(self):
        # Write the <a:off> xfrm sub-element.

        attributes = [
            ("x", 0),
            ("y", 0),
        ]

        self._xml_empty_tag("a:off", attributes)

    def _write_xfrm_extension(self):
        # Write the <a:ext> xfrm sub-element.

        attributes = [
            ("cx", 0),
            ("cy", 0),
        ]

        self._xml_empty_tag("a:ext", attributes)

    def _write_atag_graphic(self, index):
        # Write the <a:graphic> element.
        self._xml_start_tag("a:graphic")

        # Write the a:graphicData element.
        self._write_atag_graphic_data(index)

        self._xml_end_tag("a:graphic")

    def _write_atag_graphic_data(self, index):
        # Write the <a:graphicData> element.
        uri = "http://schemas.openxmlformats.org/drawingml/2006/chart"

        attributes = [
            (
                "uri",
                uri,
            )
        ]

        self._xml_start_tag("a:graphicData", attributes)

        # Write the c:chart element.
        self._write_c_chart("rId" + str(index))

        self._xml_end_tag("a:graphicData")

    def _write_c_chart(self, r_id):
        # Write the <c:chart> element.

        schema = "http://schemas.openxmlformats.org/"
        xmlns_c = schema + "drawingml/2006/chart"
        xmlns_r = schema + "officeDocument/2006/relationships"

        attributes = [
            ("xmlns:c", xmlns_c),
            ("xmlns:r", xmlns_r),
            ("r:id", r_id),
        ]

        self._xml_empty_tag("c:chart", attributes)

    def _write_client_data(self):
        # Write the <xdr:clientData> element.
        self._xml_empty_tag("xdr:clientData")

    def _write_sp(
        self,
        index,
        col_absolute,
        row_absolute,
        width,
        height,
        shape,
        description,
        url_rel_index,
        tip,
        decorative,
    ):
        # Write the <xdr:sp> element.

        if shape and shape.connect:
            attributes = [("macro", "")]
            self._xml_start_tag("xdr:cxnSp", attributes)

            # Write the xdr:nvCxnSpPr element.
            self._write_nv_cxn_sp_pr(index, shape)

            # Write the xdr:spPr element.
            self._write_xdr_sp_pr(
                index, col_absolute, row_absolute, width, height, shape
            )

            self._xml_end_tag("xdr:cxnSp")
        else:
            # Add attribute for shapes.
            attributes = [("macro", ""), ("textlink", shape.textlink)]

            self._xml_start_tag("xdr:sp", attributes)

            # Write the xdr:nvSpPr element.
            self._write_nv_sp_pr(
                index, shape, url_rel_index, tip, description, decorative
            )

            # Write the xdr:spPr element.
            self._write_xdr_sp_pr(
                index, col_absolute, row_absolute, width, height, shape
            )

            # Write the xdr:style element.
            self._write_style()

            # Write the xdr:txBody element.
            if shape.text is not None:
                self._write_tx_body(col_absolute, row_absolute, width, height, shape)

            self._xml_end_tag("xdr:sp")

    def _write_nv_cxn_sp_pr(self, index, shape):
        # Write the <xdr:nvCxnSpPr> element.
        self._xml_start_tag("xdr:nvCxnSpPr")

        name = shape.name + " " + str(index)
        if name is not None:
            self._write_c_nv_pr(index, name, None, None, None, None)

        self._xml_start_tag("xdr:cNvCxnSpPr")

        attributes = [("noChangeShapeType", "1")]
        self._xml_empty_tag("a:cxnSpLocks", attributes)

        if shape.start:
            attributes = [("id", shape.start), ("idx", shape.start_index)]
            self._xml_empty_tag("a:stCxn", attributes)

        if shape.end:
            attributes = [("id", shape.end), ("idx", shape.end_index)]
            self._xml_empty_tag("a:endCxn", attributes)

        self._xml_end_tag("xdr:cNvCxnSpPr")
        self._xml_end_tag("xdr:nvCxnSpPr")

    def _write_nv_sp_pr(
        self, index, shape, url_rel_index, tip, description, decorative
    ):
        # Write the <xdr:NvSpPr> element.
        attributes = []

        self._xml_start_tag("xdr:nvSpPr")

        name = shape.name + " " + str(index)

        self._write_c_nv_pr(
            index + 1, name, description, url_rel_index, tip, decorative
        )

        if shape.name == "TextBox":
            attributes = [("txBox", 1)]

        self._xml_empty_tag("xdr:cNvSpPr", attributes)

        self._xml_end_tag("xdr:nvSpPr")

    def _write_pic(
        self,
        index,
        rel_index,
        col_absolute,
        row_absolute,
        width,
        height,
        shape,
        description,
        url_rel_index,
        tip,
        decorative,
    ):
        # Write the <xdr:pic> element.
        self._xml_start_tag("xdr:pic")

        # Write the xdr:nvPicPr element.
        self._write_nv_pic_pr(
            index, rel_index, description, url_rel_index, tip, decorative
        )
        # Write the xdr:blipFill element.
        self._write_blip_fill(rel_index)

        # Write the xdr:spPr element.
        self._write_sp_pr(col_absolute, row_absolute, width, height, shape)

        self._xml_end_tag("xdr:pic")

    def _write_nv_pic_pr(
        self, index, rel_index, description, url_rel_index, tip, decorative
    ):
        # Write the <xdr:nvPicPr> element.
        self._xml_start_tag("xdr:nvPicPr")

        # Write the xdr:cNvPr element.
        self._write_c_nv_pr(
            index + 1,
            "Picture " + str(index),
            description,
            url_rel_index,
            tip,
            decorative,
        )

        # Write the xdr:cNvPicPr element.
        self._write_c_nv_pic_pr()

        self._xml_end_tag("xdr:nvPicPr")

    def _write_c_nv_pic_pr(self):
        # Write the <xdr:cNvPicPr> element.
        self._xml_start_tag("xdr:cNvPicPr")

        # Write the a:picLocks element.
        self._write_a_pic_locks()

        self._xml_end_tag("xdr:cNvPicPr")

    def _write_a_pic_locks(self):
        # Write the <a:picLocks> element.
        attributes = [("noChangeAspect", 1)]

        self._xml_empty_tag("a:picLocks", attributes)

    def _write_blip_fill(self, index):
        # Write the <xdr:blipFill> element.
        self._xml_start_tag("xdr:blipFill")

        # Write the a:blip element.
        self._write_a_blip(index)

        # Write the a:stretch element.
        self._write_a_stretch()

        self._xml_end_tag("xdr:blipFill")

    def _write_a_blip(self, index):
        # Write the <a:blip> element.
        schema = "http://schemas.openxmlformats.org/officeDocument/"
        xmlns_r = schema + "2006/relationships"
        r_embed = "rId" + str(index)

        attributes = [("xmlns:r", xmlns_r), ("r:embed", r_embed)]

        self._xml_empty_tag("a:blip", attributes)

    def _write_a_stretch(self):
        # Write the <a:stretch> element.
        self._xml_start_tag("a:stretch")

        # Write the a:fillRect element.
        self._write_a_fill_rect()

        self._xml_end_tag("a:stretch")

    def _write_a_fill_rect(self):
        # Write the <a:fillRect> element.
        self._xml_empty_tag("a:fillRect")

    def _write_sp_pr(self, col_absolute, row_absolute, width, height, shape=None):
        # Write the <xdr:spPr> element, for charts.

        self._xml_start_tag("xdr:spPr")

        # Write the a:xfrm element.
        self._write_a_xfrm(col_absolute, row_absolute, width, height)

        # Write the a:prstGeom element.
        self._write_a_prst_geom(shape)

        self._xml_end_tag("xdr:spPr")

    def _write_xdr_sp_pr(self, index, col_absolute, row_absolute, width, height, shape):
        # Write the <xdr:spPr> element for shapes.
        self._xml_start_tag("xdr:spPr")

        # Write the a:xfrm element.
        self._write_a_xfrm(col_absolute, row_absolute, width, height, shape)

        # Write the a:prstGeom element.
        self._write_a_prst_geom(shape)

        if shape.fill:
            if not shape.fill["defined"]:
                # Write the a:solidFill element.
                self._write_a_solid_fill_scheme("lt1")
            elif "none" in shape.fill:
                # Write the a:noFill element.
                self._xml_empty_tag("a:noFill")
            elif "color" in shape.fill:
                # Write the a:solidFill element.
                self._write_a_solid_fill(get_rgb_color(shape.fill["color"]))

        if shape.gradient:
            # Write the a:gradFill element.
            self._write_a_grad_fill(shape.gradient)

        # Write the a:ln element.
        self._write_a_ln(shape.line)

        self._xml_end_tag("xdr:spPr")

    def _write_a_xfrm(self, col_absolute, row_absolute, width, height, shape=None):
        # Write the <a:xfrm> element.
        attributes = []

        if shape:
            if shape.rotation:
                rotation = shape.rotation
                rotation *= 60000
                attributes.append(("rot", rotation))

            if shape.flip_h:
                attributes.append(("flipH", 1))
            if shape.flip_v:
                attributes.append(("flipV", 1))

        self._xml_start_tag("a:xfrm", attributes)

        # Write the a:off element.
        self._write_a_off(col_absolute, row_absolute)

        # Write the a:ext element.
        self._write_a_ext(width, height)

        self._xml_end_tag("a:xfrm")

    def _write_a_off(self, x, y):
        # Write the <a:off> element.
        attributes = [
            ("x", x),
            ("y", y),
        ]

        self._xml_empty_tag("a:off", attributes)

    def _write_a_ext(self, cx, cy):
        # Write the <a:ext> element.
        attributes = [
            ("cx", cx),
            ("cy", cy),
        ]

        self._xml_empty_tag("a:ext", attributes)

    def _write_a_prst_geom(self, shape=None):
        # Write the <a:prstGeom> element.
        attributes = [("prst", "rect")]

        self._xml_start_tag("a:prstGeom", attributes)

        # Write the a:avLst element.
        self._write_a_av_lst(shape)

        self._xml_end_tag("a:prstGeom")

    def _write_a_av_lst(self, shape=None):
        # Write the <a:avLst> element.
        adjustments = []

        if shape and shape.adjustments:
            adjustments = shape.adjustments

        if adjustments:
            self._xml_start_tag("a:avLst")

            i = 0
            for adj in adjustments:
                i += 1
                # Only connectors have multiple adjustments.
                if shape.connect:
                    suffix = i
                else:
                    suffix = ""

                # Scale Adjustments: 100,000 = 100%.
                adj_int = str(int(adj * 1000))

                attributes = [("name", "adj" + suffix), ("fmla", "val" + adj_int)]

                self._xml_empty_tag("a:gd", attributes)

            self._xml_end_tag("a:avLst")
        else:
            self._xml_empty_tag("a:avLst")

    def _write_a_solid_fill(self, rgb):
        # Write the <a:solidFill> element.
        if rgb is None:
            rgb = "FFFFFF"

        self._xml_start_tag("a:solidFill")

        # Write the a:srgbClr element.
        self._write_a_srgb_clr(rgb)

        self._xml_end_tag("a:solidFill")

    def _write_a_solid_fill_scheme(self, color, shade=None):
        attributes = [("val", color)]

        self._xml_start_tag("a:solidFill")

        if shade:
            self._xml_start_tag("a:schemeClr", attributes)
            self._write_a_shade(shade)
            self._xml_end_tag("a:schemeClr")
        else:
            self._xml_empty_tag("a:schemeClr", attributes)

        self._xml_end_tag("a:solidFill")

    def _write_a_ln(self, line):
        # Write the <a:ln> element.
        width = line.get("width", 0.75)

        # Round width to nearest 0.25, like Excel.
        width = int((width + 0.125) * 4) / 4.0

        # Convert to internal units.
        width = int(0.5 + (12700 * width))

        attributes = [("w", width), ("cmpd", "sng")]

        self._xml_start_tag("a:ln", attributes)

        if "none" in line:
            # Write the a:noFill element.
            self._xml_empty_tag("a:noFill")

        elif "color" in line:
            # Write the a:solidFill element.
            self._write_a_solid_fill(get_rgb_color(line["color"]))

        else:
            # Write the a:solidFill element.
            self._write_a_solid_fill_scheme("lt1", "50000")

        # Write the line/dash type.
        line_type = line.get("dash_type")
        if line_type:
            # Write the a:prstDash element.
            self._write_a_prst_dash(line_type)

        self._xml_end_tag("a:ln")

    def _write_tx_body(self, col_absolute, row_absolute, width, height, shape):
        # Write the <xdr:txBody> element.
        attributes = []

        if shape.text_rotation != 0:
            if shape.text_rotation == 90:
                attributes.append(("vert", "vert270"))
            if shape.text_rotation == -90:
                attributes.append(("vert", "vert"))
            if shape.text_rotation == 270:
                attributes.append(("vert", "wordArtVert"))
            if shape.text_rotation == 271:
                attributes.append(("vert", "eaVert"))

        attributes.append(("wrap", "square"))
        attributes.append(("rtlCol", "0"))

        if not shape.align["defined"]:
            attributes.append(("anchor", "t"))
        else:
            if "vertical" in shape.align:
                align = shape.align["vertical"]
                if align == "top":
                    attributes.append(("anchor", "t"))
                elif align == "middle":
                    attributes.append(("anchor", "ctr"))
                elif align == "bottom":
                    attributes.append(("anchor", "b"))
            else:
                attributes.append(("anchor", "t"))

            if "horizontal" in shape.align:
                align = shape.align["horizontal"]
                if align == "center":
                    attributes.append(("anchorCtr", "1"))
            else:
                attributes.append(("anchorCtr", "0"))

        self._xml_start_tag("xdr:txBody")
        self._xml_empty_tag("a:bodyPr", attributes)
        self._xml_empty_tag("a:lstStyle")

        lines = shape.text.split("\n")

        # Set the font attributes.
        font = shape.font
        style_attrs = Shape._get_font_style_attributes(font)
        latin_attrs = Shape._get_font_latin_attributes(font)
        style_attrs.insert(0, ("lang", font["lang"]))

        if shape.textlink != "":
            attributes = [
                ("id", "{B8ADDEFE-BF52-4FD4-8C5D-6B85EF6FF707}"),
                ("type", "TxLink"),
            ]

            self._xml_start_tag("a:p")
            self._xml_start_tag("a:fld", attributes)

            self._write_font_run(font, style_attrs, latin_attrs, "a:rPr")

            self._xml_data_element("a:t", shape.text)
            self._xml_end_tag("a:fld")

            self._write_font_run(font, style_attrs, latin_attrs, "a:endParaRPr")

            self._xml_end_tag("a:p")
        else:
            for line in lines:
                self._xml_start_tag("a:p")

                if line == "":
                    self._write_font_run(font, style_attrs, latin_attrs, "a:endParaRPr")
                    self._xml_end_tag("a:p")
                    continue
                elif "text" in shape.align:
                    if shape.align["text"] == "left":
                        self._xml_empty_tag("a:pPr", [("algn", "l")])
                    if shape.align["text"] == "center":
                        self._xml_empty_tag("a:pPr", [("algn", "ctr")])
                    if shape.align["text"] == "right":
                        self._xml_empty_tag("a:pPr", [("algn", "r")])

                self._xml_start_tag("a:r")

                self._write_font_run(font, style_attrs, latin_attrs, "a:rPr")

                self._xml_data_element("a:t", line)

                self._xml_end_tag("a:r")
                self._xml_end_tag("a:p")

        self._xml_end_tag("xdr:txBody")

    def _write_font_run(self, font, style_attrs, latin_attrs, run_type):
        # Write a:rPr or a:endParaRPr.
        if font.get("color") is not None:
            has_color = True
        else:
            has_color = False

        if latin_attrs or has_color:
            self._xml_start_tag(run_type, style_attrs)

            if has_color:
                self._write_a_solid_fill(get_rgb_color(font["color"]))

            if latin_attrs:
                self._write_a_latin(latin_attrs)
                self._write_a_cs(latin_attrs)

            self._xml_end_tag(run_type)
        else:
            self._xml_empty_tag(run_type, style_attrs)

    def _write_style(self):
        # Write the <xdr:style> element.
        self._xml_start_tag("xdr:style")

        # Write the a:lnRef element.
        self._write_a_ln_ref()

        # Write the a:fillRef element.
        self._write_a_fill_ref()

        # Write the a:effectRef element.
        self._write_a_effect_ref()

        # Write the a:fontRef element.
        self._write_a_font_ref()

        self._xml_end_tag("xdr:style")

    def _write_a_ln_ref(self):
        # Write the <a:lnRef> element.
        attributes = [("idx", "0")]

        self._xml_start_tag("a:lnRef", attributes)

        # Write the a:scrgbClr element.
        self._write_a_scrgb_clr()

        self._xml_end_tag("a:lnRef")

    def _write_a_fill_ref(self):
        # Write the <a:fillRef> element.
        attributes = [("idx", "0")]

        self._xml_start_tag("a:fillRef", attributes)

        # Write the a:scrgbClr element.
        self._write_a_scrgb_clr()

        self._xml_end_tag("a:fillRef")

    def _write_a_effect_ref(self):
        # Write the <a:effectRef> element.
        attributes = [("idx", "0")]

        self._xml_start_tag("a:effectRef", attributes)

        # Write the a:scrgbClr element.
        self._write_a_scrgb_clr()

        self._xml_end_tag("a:effectRef")

    def _write_a_scrgb_clr(self):
        # Write the <a:scrgbClr> element.

        attributes = [
            ("r", "0"),
            ("g", "0"),
            ("b", "0"),
        ]

        self._xml_empty_tag("a:scrgbClr", attributes)

    def _write_a_font_ref(self):
        # Write the <a:fontRef> element.
        attributes = [("idx", "minor")]

        self._xml_start_tag("a:fontRef", attributes)

        # Write the a:schemeClr element.
        self._write_a_scheme_clr("dk1")

        self._xml_end_tag("a:fontRef")

    def _write_a_scheme_clr(self, val):
        # Write the <a:schemeClr> element.
        attributes = [("val", val)]

        self._xml_empty_tag("a:schemeClr", attributes)

    def _write_a_shade(self, shade):
        # Write the <a:shade> element.
        attributes = [("val", shade)]

        self._xml_empty_tag("a:shade", attributes)

    def _write_a_prst_dash(self, val):
        # Write the <a:prstDash> element.

        attributes = [("val", val)]

        self._xml_empty_tag("a:prstDash", attributes)

    def _write_a_grad_fill(self, gradient):
        # Write the <a:gradFill> element.

        attributes = [("flip", "none"), ("rotWithShape", "1")]

        if gradient["type"] == "linear":
            attributes = []

        self._xml_start_tag("a:gradFill", attributes)

        # Write the a:gsLst element.
        self._write_a_gs_lst(gradient)

        if gradient["type"] == "linear":
            # Write the a:lin element.
            self._write_a_lin(gradient["angle"])
        else:
            # Write the a:path element.
            self._write_a_path(gradient["type"])

            # Write the a:tileRect element.
            self._write_a_tile_rect(gradient["type"])

        self._xml_end_tag("a:gradFill")

    def _write_a_gs_lst(self, gradient):
        # Write the <a:gsLst> element.
        positions = gradient["positions"]
        colors = gradient["colors"]

        self._xml_start_tag("a:gsLst")

        for i in range(len(colors)):
            pos = int(positions[i] * 1000)
            attributes = [("pos", pos)]
            self._xml_start_tag("a:gs", attributes)

            # Write the a:srgbClr element.
            color = get_rgb_color(colors[i])
            self._write_a_srgb_clr(color)

            self._xml_end_tag("a:gs")

        self._xml_end_tag("a:gsLst")

    def _write_a_lin(self, angle):
        # Write the <a:lin> element.

        angle = int(60000 * angle)

        attributes = [
            ("ang", angle),
            ("scaled", "0"),
        ]

        self._xml_empty_tag("a:lin", attributes)

    def _write_a_path(self, gradient_type):
        # Write the <a:path> element.

        attributes = [("path", gradient_type)]

        self._xml_start_tag("a:path", attributes)

        # Write the a:fillToRect element.
        self._write_a_fill_to_rect(gradient_type)

        self._xml_end_tag("a:path")

    def _write_a_fill_to_rect(self, gradient_type):
        # Write the <a:fillToRect> element.

        if gradient_type == "shape":
            attributes = [
                ("l", "50000"),
                ("t", "50000"),
                ("r", "50000"),
                ("b", "50000"),
            ]
        else:
            attributes = [
                ("l", "100000"),
                ("t", "100000"),
            ]

        self._xml_empty_tag("a:fillToRect", attributes)

    def _write_a_tile_rect(self, gradient_type):
        # Write the <a:tileRect> element.

        if gradient_type == "shape":
            attributes = []
        else:
            attributes = [
                ("r", "-100000"),
                ("b", "-100000"),
            ]

        self._xml_empty_tag("a:tileRect", attributes)

    def _write_a_srgb_clr(self, val):
        # Write the <a:srgbClr> element.

        attributes = [("val", val)]

        self._xml_empty_tag("a:srgbClr", attributes)

    def _write_a_latin(self, attributes):
        # Write the <a:latin> element.
        self._xml_empty_tag("a:latin", attributes)

    def _write_a_cs(self, attributes):
        # Write the <a:latin> element.
        self._xml_empty_tag("a:cs", attributes)
