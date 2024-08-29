# -*- coding: utf-8 -*-
from odoo.addons import hr
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class HrDepartment(models.Model, hr.HrDepartment):

    # Get department name using superuser, because model is not accessible for portal users
    display_name = fields.Char(compute='_compute_display_name', compute_sudo=True)
