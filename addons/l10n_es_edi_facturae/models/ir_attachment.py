from odoo import models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _identify_and_unwrap_file(self, file_data):
        """ If the file is a Factura-E XML, set the decoder. """
        # EXTENDS 'account'
        def is_facturae(tree):
            return tree.tag in [
                '{http://www.facturae.es/Facturae/2014/v3.2.1/Facturae}Facturae',
                '{http://www.facturae.gob.es/formato/Versiones/Facturaev3_2_2.xml}Facturae',
            ]

        if 'xml_tree' in file_data and is_facturae(file_data['xml_tree']):
            return [{**file_data, 'type': 'l10n_es.facturae', 'decoder': self.env['account.move']._import_invoice_facturae, 'priority': 20}]

        return super()._identify_and_unwrap_file(file_data)
