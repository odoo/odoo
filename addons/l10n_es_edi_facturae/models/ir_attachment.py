from lxml import etree

from odoo import models

from odoo.addons.account.models.ir_attachment import split_etree_on_tag


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _get_import_type_and_priority(self):
        """ Identify Factura-E files. """
        # EXTENDS 'account'
        def is_facturae(tree):
            return tree.tag in [
                '{http://www.facturae.es/Facturae/2014/v3.2.1/Facturae}Facturae',
                '{http://www.facturae.gob.es/formato/Versiones/Facturaev3_2_2.xml}Facturae',
            ]

        if self.xml_tree is not False and is_facturae(self.xml_tree):
            return ('l10n_es.facturae', 20)

        return super()._get_import_type_and_priority()

    def _unwrap_attachment(self):
        """ Divide a Facturae file into constituent invoices and create a new attachment for each invoice after the first. """
        # EXTENDS 'account'
        if self.import_type == 'l10n_es.facturae' and len(self.xml_tree.findall('.//Invoice')) > 1:
            # Create a new attachment for each invoice beyond the first.
            trees = split_etree_on_tag(self.xml_tree, 'Invoice')
            filename_without_extension, dummy, extension = self.name.rpartition('.')
            attachment_vals = [
                {
                    'name': f'{filename_without_extension}_{filename_index}.{extension}',
                    'raw': etree.tostring(tree),
                    'xml_tree': tree,
                }
                for filename_index, tree in enumerate(trees[1:], start=2)
            ]
            return self.create(attachment_vals)

        return super()._unwrap_attachment()
