from odoo import api, models
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

    def _to_files_data(self):
        files_data = []
        for attachment in self:
            file_data = {
                'name': attachment.name,
                'raw': attachment.raw,
                'mimetype': attachment.mimetype,
                'origin_attachment': attachment,
                'attachment': attachment,
            }
            file_data['xml_tree'] = self._get_xml_tree(file_data)
            file_data['import_file_type'] = self._get_import_file_type(file_data)
            file_data['origin_import_file_type'] = file_data['import_file_type']
            files_data.append(file_data)
        return files_data

    @api.model
    def _from_files_data(self, files_data):
        return self.browse().union(*(
            file_data['attachment']
            for file_data in files_data
            if file_data.get('attachment')
        ))

    @api.model
    def _get_import_file_type(self, file_data):
        if 'pdf' in file_data['mimetype'] or file_data['name'].endswith('.pdf'):
            return 'pdf'

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

    @api.model
    def _get_xml_tree(self, file_data):
        if (
            # XML attachments received by mail have a 'text/plain' mimetype.
            'text/plain' in file_data['mimetype'] and (guess_mimetype(file_data['raw']).endswith('/xml') or file_data['name'].endswith('.xml'))
            or file_data['mimetype'].endswith('/xml')
        ):
            try:
                return etree.fromstring(file_data['raw'])
            except etree.ParseError as e:
                _logger.info('Error when reading the xml file "%s": %s', file_data['name'], e)

    @api.model
    def _unwrap_attachments(self, files_data, recurse=True):
        """ Unwrap and return any embedded attachments.

        :param recurse: if True, embedded-of-embedded attachments will also be unwrapped and returned.
        :return: an ir.attachment recordset of the embedded attachments.
        """
        embedded = []
        for file_data in files_data:
            if file_data['import_file_type'] == 'pdf':
                with io.BytesIO(file_data['raw']) as buffer:
                    try:
                        pdf_reader = OdooPdfFileReader(buffer, strict=False)
                    except Exception as e:
                        # Malformed pdf
                        _logger.info('Error when reading the pdf file "%s": %s', file_data['name'], e)
                    else:
                        try:
                            for filename, content in pdf_reader.getAttachments():
                                file_data = {
                                    'name': filename,
                                    'raw': content,
                                    'mimetype': guess_mimetype(content),
                                    'attachment': None,
                                    'origin_attachment': file_data['origin_attachment'],
                                    'origin_import_file_type': file_data['origin_import_file_type'],
                                }
                                file_data['xml_tree'] = self._get_xml_tree(file_data)
                                file_data['import_file_type'] = self._get_import_file_type(file_data)

                                embedded.append(file_data)

                        except (NotImplementedError, StructError, PdfReadError) as e:
                            _logger.warning("Unable to access the attachments of %s. Tried to decrypt it, but %s.", file_data['name'], e)

        if embedded and recurse:
            embedded.extend(self._unwrap_attachments(embedded, recurse=True))
        return embedded

    def _post_add_create(self, **kwargs):
        for move_id, attachments in self.filtered(lambda attachment: attachment.res_model == 'account.move').grouped('res_id').items():
            files_data = attachments._to_files_data()
            files_data.extend(self.env['ir.attachment']._unwrap_attachments(files_data))
            self.env['account.move'].browse(move_id)._extend_with_attachments(files_data)
        super()._post_add_create(**kwargs)
