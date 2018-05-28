# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    has_group_intrastat_extended = fields.Boolean(
        'Intrastat extended', compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='l10n_be_intrastat.intrastat_extended')
