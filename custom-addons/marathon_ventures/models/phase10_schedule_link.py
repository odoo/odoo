# -*- coding: utf-8 -*-
"""Phase 10 - link mv.schedules to mv.deal_line so the Units Grid OWL
widget can roll up units_available per (deal_line, week) cell.

Cascade ondelete: when a Deal Line is removed, its linked Schedule rows
are automatically dropped too. This is what makes "delete row" in the
Units Grid actually clean up the database.
"""
from odoo import models, fields


class MvScheduleDealLineLink(models.Model):
    _name = 'mv.schedules'
    _inherit = 'mv.schedules'

    deal_line_id = fields.Many2one(
        comodel_name='mv.deal_line',
        string='Deal Line',
        ondelete='cascade',
        index=True,
    )
