# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from email.policy import default
from odoo import fields, models, _, api
from odoo.exceptions import UserError


class ImportStore(models.Model):
    _name = "sh.import.store"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "The Base Module to store all the records"

    base_id = fields.Many2one("sh.import.base", string="Base")
    base_name = fields.Char("Name", related="base_id.name", store=True)
    sh_file = fields.Binary("Upload File", tracking=True)
    name = fields.Char(string="Number", readonly=True,
                       required=True, copy=False, default='New')
    state = fields.Selection([('draft', 'Draft'), ('in_progress', 'In Progress'), ('running', 'Running'), (
        'partial_done', 'Partial Done'), ('done', 'Done'), ('error', 'Error')], string='State', default="draft", tracking=True)
    import_logger_line = fields.One2many("sh.import.log", "sh_store_id")
    count_start_from = fields.Integer("Count Starts From", default=1)
    current_count = fields.Integer("Current Count", default=0)
    import_limit = fields.Integer(
        "Import Limit", related="base_id.import_limit", readonly=False)
    on_error = fields.Selection(
        related="base_id.on_error", string="On Error", readonly=False)
    received_error = fields.Boolean("Received Error", default=False)

    @api.model_create_multi
    def create(self, vals):
        for val in vals:
            if val.get('name', 'New') == 'New':
                val['name'] = self.env['ir.sequence'].next_by_code(
                    'sh.import.store') or 'New'
            result = super(ImportStore, self).create(val)
        return result

    def action_perform(self):
        get_record = self.search([('state', '=', 'running')], limit=1)
        if not get_record:
            get_record = self.search([('state', '=', 'in_progress')], limit=1)
        if get_record:
            get_record.state = "running"
            self.perform_the_action(get_record)

    def perform_the_action(self, record):
        print(record)

    def reset_draft(self):
        self.state = 'draft'

    def sent_inprogress(self):
        self.state = 'in_progress'

    def import_store_manually(self):
        if self.import_limit != 0:
            raise UserError(_("Please Make Import Limit 0 to Force Import"))
        self.perform_the_action(self)
