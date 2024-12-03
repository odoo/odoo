from odoo import api, fields, models
from odoo.tools.pdf import OdooPdfFileReader, PdfReadError
from odoo.tools.mimetypes import guess_mimetype

from copy import deepcopy
from lxml import etree
from struct import error as StructError
import io
import logging
import zipfile

_logger = logging.getLogger(__name__)


def split_etree_on_tag(tree, tag):
    """ Split an etree that has multiple instances of a given tag into multiple trees
    that each have a single instance of the tag. """
    tree = deepcopy(tree)
    nodes_to_split = tree.findall(f'.//{tag}')

    # Remove all nodes with the tag
    parent_node = nodes_to_split[0].getparent()
    for node in nodes_to_split:
        parent_node.remove(node)

    # Create a new tree for each node
    trees = []
    for node in nodes_to_split:
        parent_node.append(node)
        trees.append(deepcopy(tree))
        parent_node.remove(node)
    return trees


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    import_type = fields.Char(
        string="File type for import",
        help="Technical field, used by the import framework to call the appropriate decoder.",
        compute='_compute_import_type_and_priority',
    )
    import_priority = fields.Integer(
        string="Import priority",
        help="Technical field indicating the priority with which this attachment should be decoded on an invoice.",
        compute='_compute_import_type_and_priority',
    )
    xml_tree = fields.Binary(
        string="XML tree for import",
        help="Technical field containing the lxml.etree of the attachment, to avoid needing to recompute it.",
        compute='_compute_xml_tree',
    )
    root_attachment_id = fields.Many2one(
        string="Root attachment",
        help="Technical field indicating the attachment from which this embedded attachment was extracted.",
        comodel_name='ir.attachment',
        store=False,  # only needed during invoice import, so we keep it cache-only.
    )

    @api.depends('name', 'mimetype', 'raw')
    def _compute_import_type_and_priority(self):
        for attachment in self:
            attachment.import_type, attachment.import_priority = attachment._get_import_type_and_priority()

    @api.depends('raw')
    def _compute_xml_tree(self):
        for attachment in self:
            xml_tree = attachment._get_xml_tree()
            attachment.xml_tree = xml_tree if xml_tree is not None else False

    def _get_import_type_and_priority(self):
        if 'pdf' in self.mimetype or self.name.endswith('.pdf'):
            return 'pdf', 10
        return False, 0

    def _build_zip_from_attachments(self):
        """ Return the zip bytes content resulting from compressing the attachments in `self`"""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as zipfile_obj:
            for attachment in self:
                zipfile_obj.writestr(attachment.display_name, attachment.raw)
        return buffer.getvalue()

    # -------------------------------------------------------------------------
    # EDI
    # -------------------------------------------------------------------------

    def _get_xml_tree(self):
        if (
            # XML attachments received by mail have a 'text/plain' mimetype.
            'text/plain' in self.mimetype and (guess_mimetype(self.raw).endswith('/xml') or self.name.endswith('.xml'))
            or self.mimetype.endswith('/xml')
        ):
            try:
                return etree.fromstring(self.raw)
            except etree.ParseError as e:
                _logger.info('Error when reading the xml file "%s": %s', self.name, e)

    def _get_embedded_attachments(self):
        """ Extract all the embedded attachments of `self` into ir.attachment records,
        by recursively calling `_unwrap_attachments`.

        The resulting records can be `new` records or in-database records.
        """
        embedded = self.env['ir.attachment'].union(*(a._unwrap_attachment() for a in self))

        # Recursively call until all embedded-of-embedded attachments have been unwrapped.
        if embedded:
            embedded |= embedded._get_embedded_attachments()
        return embedded

    def _unwrap_attachment(self):
        """ Unwrap any embedded files that can be found in the given attachment.

        This method can be extended to handle the unwrapping of various file formats.

        The resulting attachments can be `new` records if we don't intend to save them to DB,
        or can be in-database records.

        The `root_attachment_id` field should be set on the returned attachments if they should
        be grouped with their parent attachment when determining how to dispatch attachments into
        invoices. Otherwise, it should not be set.

        :return: an ir.attachment recordset of the embedded attachments.
        """
        self.ensure_one()
        if self.import_type == 'pdf':
            with io.BytesIO(self.raw) as buffer:
                try:
                    pdf_reader = OdooPdfFileReader(buffer, strict=False)
                except Exception as e:
                    # Malformed pdf
                    _logger.info('Error when reading the pdf file "%s": %s', self.name, e)
                    return self.browse()

                # Process embedded files.
                try:
                    return self.env['ir.attachment'].union(*(
                        # We create these as NewRecords so they will never be saved to database.
                        self.new({
                            'name': filename,
                            'raw': content,
                            'mimetype': guess_mimetype(content),
                            'root_attachment_id': self.root_attachment_id.id or self.id,
                        })
                        for filename, content in pdf_reader.getAttachments()
                    ))

                except (NotImplementedError, StructError, PdfReadError) as e:
                    _logger.warning("Unable to access the attachments of %s. Tried to decrypt it, but %s.", self.name, e)
                    return self.browse()
        return self.browse()

    def _post_add_create(self, **kwargs):
        for move_id, attachments in self.filtered(lambda attachment: attachment.res_model == 'account.move').grouped('res_id').items():
            attachments |= attachments._get_embedded_attachments()
            self.env['account.move'].browse(move_id)._extend_with_attachments(attachments)
        super()._post_add_create(**kwargs)
