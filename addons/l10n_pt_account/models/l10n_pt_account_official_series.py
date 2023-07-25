from odoo import models, fields, _
from odoo.exceptions import UserError


class L10nPtAccountOfficialSeries(models.Model):
    _name = "l10n_pt_account.official.series"
    _description = "Official Series provided by the Portuguese Tax Authority"
    _rec_name = 'code'

    code = fields.Char("Code of the series", required=True)
    end_date = fields.Date("End Date of the series")
    active = fields.Boolean(default=True)

    _sql_constraints = [('code', 'unique(code)', 'Code must be unique.')]

    def write(self, vals):
        res = super().write(vals)
        for official_series in self:
            if vals.get('code') and official_series.code:
                raise UserError(_("You cannot change the code of a series."))
        return res
