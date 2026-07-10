from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_cr_fe_identification_type = fields.Selection(
        selection=[('01', 'Física'), ('02', 'Jurídica'), ('03', 'DIMEX'), ('04', 'NITE')],
        string="Tipo de identificación FE", default='01',
        help="Tipo de identificación del cliente para Factura Electrónica de Hacienda.")
