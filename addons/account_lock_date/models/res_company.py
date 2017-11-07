# -*- coding: utf-8 -*-

import time

from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo import api, models, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.multi
    def write(self, vals):
        # fiscalyear_lock_date can't be set to a prior date
        if vals.get('fiscalyear_lock_date'):
            self._check_irreversibility_lock_dates(vals['fiscalyear_lock_date'])
        return super(ResCompany, self).write(vals)

    def _check_irreversibility_lock_dates(self, fiscalyear_lock_date):
        # Check the irreversibility of the lock date for all users
        if not self.fiscalyear_lock_date:
            return

        comp_fy_time = time.strptime(self.fiscalyear_lock_date, DEFAULT_SERVER_DATE_FORMAT)
        if fiscalyear_lock_date:
            fy_time = time.strptime(fiscalyear_lock_date, DEFAULT_SERVER_DATE_FORMAT)
            if fy_time < comp_fy_time:
                raise ValidationError(_('The lock date for all users is irreversible and must be strictly higher than the previous date.'))
        else:
            raise ValidationError(_('The lock date for all users is irreversible and can\'t be removed'))
