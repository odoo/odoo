# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import hr


class ResCompany(hr.ResCompany):

    hr_presence_last_compute_date = fields.Datetime()
