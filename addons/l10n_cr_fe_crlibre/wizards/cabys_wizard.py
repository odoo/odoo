from odoo import _, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_cr_fe_crlibre.models.cabys_client import CabysApiError


class L10nCrFeCabysWizard(models.TransientModel):
    _name = 'l10n_cr.fe.cabys.wizard'
    _description = "Buscador de códigos CABYS (Hacienda)"

    product_id = fields.Many2one('product.template', required=True, readonly=True)
    query = fields.Char(string="Buscar (texto o código CABYS)")
    searched = fields.Boolean(default=False)
    result_ids = fields.One2many('l10n_cr.fe.cabys.wizard.line', 'wizard_id')

    def action_buscar(self):
        self.ensure_one()
        client = self.env['l10n_cr.fe.cabys.client']
        try:
            resultados = client.buscar(self.query)
        except CabysApiError as exc:
            raise UserError(str(exc))
        self.result_ids = [(5, 0, 0)] + [(0, 0, {
            'codigo': r['codigo'], 'descripcion': r['descripcion'], 'impuesto': r['impuesto'],
        }) for r in resultados]
        self.searched = True
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'l10n_cr.fe.cabys.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }


class L10nCrFeCabysWizardLine(models.TransientModel):
    _name = 'l10n_cr.fe.cabys.wizard.line'
    _description = "Resultado de búsqueda CABYS"

    wizard_id = fields.Many2one('l10n_cr.fe.cabys.wizard', required=True, ondelete='cascade')
    codigo = fields.Char(readonly=True)
    descripcion = fields.Char(readonly=True)
    impuesto = fields.Float(string="IVA %", readonly=True)

    def action_usar(self):
        self.ensure_one()
        product = self.wizard_id.product_id
        product.write({
            'l10n_cr_fe_cabys': self.codigo,
            'l10n_cr_fe_cabys_descripcion': self.descripcion,
        })
        tax = self.env['account.tax'].search([
            ('type_tax_use', '=', 'sale'),
            ('amount', '=', self.impuesto),
            ('company_id', '=', self.env.company.id),
        ], limit=1)
        if tax:
            product.taxes_id = [(6, 0, tax.ids)]
        else:
            product.message_post(body=_(
                "Código CABYS %s asignado (IVA %.2f%%), pero no existe un impuesto de venta "
                "con esa tarifa configurado en Odoo. Configúrelo para que se use en las facturas."
            ) % (self.codigo, self.impuesto))
        return {'type': 'ir.actions.act_window_close'}
