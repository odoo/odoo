# -*- coding: utf-8 -*-

from odoo import models, fields, api,_

class NationalIDApplication(models.Model):
    _name = 'national.application'
    _description = 'National ID Application'
    _inherit =["mail.thread", "mail.activity.mixin"]
    _order = "create_date DESC"
    
    name = fields.Char("Ref", default=_("New"))
    applicant_name = fields.Char(string="Applicant Name", )
    date_of_birth = fields.Date(string="Date of Birth", )
    country_id = fields.Many2one("res.country")
    address = fields.Text(string="Address", )
    email = fields.Char(string="Email", )
    applicant_phone = fields.Char(string="Application Phone",)
    picture = fields.Binary(string="Picture")
    lc_reference_letter = fields.Binary(string="LC Reference Letter")
    village = fields.Char("Village")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('first_approval', 'First Approval'),
        ('second_approval', 'Second Approval'),
        ('approved', 'Approved'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected')],
        string='Status', default='draft', tracking=True, index=True, copy=False)

    def action_submit(self):
        self.ensure_one()
        self.write({'state': 'first_approval',})

    def action_first_approval(self):
        self.ensure_one()
        self.write({'state': 'second_approval',})

    def action_second_approval(self):
        self.ensure_one()
        self.write({'state': 'approved',})

    def action_reject(self):
        self.ensure_one()
        self.write({'state': 'rejected'})
        
    def action_done(self):
        self.ensure_one()
        self.write({'state': 'completed'})
        
    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code("national.application")
        res = super(NationalIDApplication, self).create(vals)
        return res