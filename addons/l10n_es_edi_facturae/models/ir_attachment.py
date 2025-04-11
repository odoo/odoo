from lxml import etree

from odoo import models

from odoo.addons.account.models.ir_attachment import split_etree_on_tag


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _get_import_file_type(self, file_data):
        """ Identify Factura-E files. """
        # EXTENDS 'account'
        def is_facturae(tree):
            return tree.tag in [
                '{http://www.facturae.es/Facturae/2014/v3.2.1/Facturae}Facturae',
                '{http://www.facturae.gob.es/formato/Versiones/Facturaev3_2_2.xml}Facturae',
            ]

        if file_data['xml_tree'] is not None and is_facturae(file_data['xml_tree']):
            return 'l10n_es.facturae'

        return super()._get_import_file_type(file_data)

    def _unwrap_attachments(self, files_data, recurse=True):
        """ Divide a Facturae file into constituent invoices and create a new attachment for each invoice after the first. """
        # EXTENDS 'account'
        embedded = super()._unwrap_attachments(files_data, recurse=False)

        for file_data in files_data:
            if file_data['import_file_type'] == 'l10n_es.facturae' and len(file_data['xml_tree'].findall('.//Invoice')) > 1:
                # Create a new attachment for each invoice beyond the first.
                trees = split_etree_on_tag(file_data['xml_tree'], 'Invoice')
                filename_without_extension, dummy, extension = file_data['name'].rpartition('.')
                attachment_vals = [
                    {
                        'name': f'{filename_without_extension}_{filename_index}.{extension}',
                        'raw': etree.tostring(tree),
                    }
                    for filename_index, tree in enumerate(trees[1:], start=2)
                ]
                created_attachments = self.create(attachment_vals)
                embedded.extend(created_attachments._to_files_data())

        if embedded and recurse:
            embedded.extend(self._unwrap_attachments(embedded, recurse=True))
        return embedded
