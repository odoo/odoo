from odoo import api, fields, models

class LeadVote(models.Model):
    _name = 'crm.lead.vote'
    _description = 'CRM Lead Vote'

    field = fields.Char(required=True)
    value = fields.Char(required=True)
    domain_id = fields.Many2one('crm.lead.domain', required=True, ondelete='cascade')

class DomainVote(models.Model):
    _name = 'crm.lead.domain'
    _description = 'CRM Lead Domain'

    name = fields.Char(required=True)

    _sql_constraints = [('name_unique', 'unique(name)', "Name must be unique !")]