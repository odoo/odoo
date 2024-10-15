# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import hr


class HrEmployee(hr.HrEmployee):

    l10n_mx_curp = fields.Char('CURP', groups="hr.group_hr_user", tracking=True)
    l10n_mx_rfc = fields.Char('RFC', groups="hr.group_hr_user", tracking=True)
