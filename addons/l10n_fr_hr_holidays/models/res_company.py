# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _default_work_entry_type_id(self):
        return self.env.ref('hr_holidays.l10n_fr_work_entry_type_paid_time_off', raise_if_not_found=False)

    l10n_fr_reference_work_entry_type = fields.Many2one(
        'hr.work.entry.type',
        string='Company Paid Time Type',
        default=_default_work_entry_type_id)

    def _get_fr_reference_work_entry_type(self):
        self.ensure_one()
        if not self.l10n_fr_reference_work_entry_type:
            default_type = self._default_work_entry_type_id()
            if not default_type:
                raise ValidationError(_("You must first define a reference time type for the company."))
            return default_type
        return self.l10n_fr_reference_work_entry_type
