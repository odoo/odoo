from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import datetime
import logging
# from dateutil.relativedelta import relativedelta
_logger = logging.getLogger(__name__)


class L10n_ArPartnerTax(models.Model):
    _name = 'l10n_ar.partner.tax'
    _description = "Argentinean Partner Taxes"
    _order = "to_date desc, from_date desc, tax_id"
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of

    partner_id = fields.Many2one(
        'res.partner',
        required=True,
        ondelete='cascade',
        check_company=True,
    )
    tax_id = fields.Many2one(
        'account.tax',
        required=True,
    )
    company_id = fields.Many2one(
        related='tax_id.company_id', store=True,
    )
    from_date = fields.Date(
        string="From Date"
    )
    to_date = fields.Date(
        string="To Date"
    )
    ref = fields.Char(
        string="ref"
    )

    @api.constrains('from_date', 'to_date')
    def check_partner_tax_dates(self):
        if self.filtered(lambda x: x.from_date and x.to_date and x.from_date >= x.to_date):
            raise ValidationError(_('"From date" must be lower than "To date" on Withholding (AR) taxes.'))

    @api.constrains('partner_id', 'tax_id', 'from_date', 'to_date')
    def _check_tax_group_overlap(self):
        for record in self:
            domain = [
                ('id', '!=', record.id),
                ('partner_id', '=', record.partner_id.id),
                ('tax_id.tax_group_id', '=', record.tax_id.tax_group_id.id),
                '&',
                '|', ('from_date', '=', False), ('from_date', '<=', record.to_date or datetime.date.max),
                '|', ('to_date', '=', False), ('to_date', '>=', record.from_date or datetime.date.min),
            ]
            if self.tax_id.l10n_ar_withholding_payment_type == 'supplier':
                # TODO esto lo deberiamos borrar al ir a odoo 19 y solo usar los tax groups
                # por ahora, para no renegar con scripts de migra que requieran crear tax groups para cada jurisdiccion y
                # ademas luego tener que ajustar a lo que hagamos en 19, usamos la jursdiccion como elemento de agrupacion
                # solo para retenciones
                domain += [('tax_id.l10n_ar_state_id', '=', self.tax_id.l10n_ar_state_id.id)]
            conflicting_records = self.search(domain)
            if conflicting_records:
                raise ValidationError(
                    "No puede haber dos impuestos del mismo grupo vigentes en el mismo momento para la misma empresa. "
                    "Tal vez tenga algun impuesto al que le tenga que definir una fecha hasta. Más información:\n"
                    "* Impuesto: %s\n"
                    "* Fecha Hasta: %s\n"
                    "* Fecha Desde: %s\n"
                    "* Otros impuestos: %s\n" % (record.tax_id.name, record.to_date, record.from_date, conflicting_records.mapped('tax_id.name'))
                )
