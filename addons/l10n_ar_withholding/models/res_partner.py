from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    # TODO renombrar campo
    arba_alicuot_ids = fields.One2many(
        'res.partner.arba_alicuot',
        'partner_id',
        'Alícuotas PERC-RET',
    )
    drei = fields.Selection([
        ('activo', 'Activo'),
        ('no_activo', 'No Activo'),
    ],
        string='DREI',
    )
    # TODO agregarlo en mig a v10 ya que fix dbs no es capaz de arreglarlo
    # porque da el error antes de empezar a arreglar
    # drei_number = fields.Char(
    # )
    default_regimen_ganancias_id = fields.Many2one(
        'afip.tabla_ganancias.alicuotasymontos',
        'Regimen Ganancias por Defecto',
    )

    @api.constrains('arba_alicuot_ids')
    def _avoid_repeated_aliquots(self):
        for arba_alicuot in self.arba_alicuot_ids:
            if arba_alicuot.from_date and arba_alicuot.to_date and arba_alicuot.from_date > arba_alicuot.to_date:
                    raise ValidationError('The start date cannot be after the end date.')
            existing_alicuot = self.arba_alicuot_ids.search([
                ('tax_id', '=', arba_alicuot.tax_id.id),
                ('to_date',  '>=', arba_alicuot.from_date or arba_alicuot.to_date),
                ('from_date', '<=', arba_alicuot.to_date or arba_alicuot.from_date),
                ('id', '!=', arba_alicuot.id)
            ])
            if existing_alicuot:
                raise ValidationError('The date range overlaps with an existing record for the same tax.')
