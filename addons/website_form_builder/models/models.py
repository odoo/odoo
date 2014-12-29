# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp import tools

class website_config(models.Model):
    """ add a config boolean needed to Enable/Disable metadata writing on save """
    _inherit = 'website'
    website_form_enable_metadata = fields.Boolean('Write metadata',help="Enable/Disable writting metadata on default_field")

class website_model(models.Model):
    """ Model configuration for form builder """
    _name = 'ir.model'
    _inherit = 'ir.model'

    website_form_access             = fields.Boolean('Public form access', help='Enable/Disable insert from public form')
    website_form_default_field_id   = fields.Many2one('ir.model.fields', 'Default Field', ondelete='set null', help="Specify the field wich will contain meta and custom datas")
    website_form_label              = fields.Char("Kind of action", help="Label to describe the action",translate=True)

    def all_inherited_field_domain(self):
        domain = []
        op = []
        domain.append(('model_id', '=', self.id))
        for val in self.inherited_model_ids:
            domain.append(('model_id', '=', val.id))
            op.append('|')
            child_dom = val.all_inherited_field_domain()
            if child_dom['domain']:
                op.append('|')
                domain = domain + child_dom['domain']
                op = op + child_dom['op']
        return {'op': op, 'domain':domain}

    @api.multi
    def get_authorized_fields(self):
        model = self.env[self.model]
        output = model.fields_get()
        domain = self.all_inherited_field_domain()
        domain = domain['op'] + domain['domain'];
        domain.append(('website_form_blacklisted_register', '=', False))
        
        # for elem in blacklist
        for elem in self.env['ir.model.fields'].search(domain):
            if elem.website_form_blacklisted:
                output.pop(elem.name, None)
        for key, val in model._inherits.iteritems():
            output.pop(val,None)
        return output

class website_model_fields(models.Model):
    """ fields configuration for form builder """
    _name = 'ir.model.fields'
    _inherit = 'ir.model.fields'

    website_form_blacklisted_register   = fields.Boolean('Blacklisted Field', help='Blacklist the Field')
    website_form_blacklisted            = fields.Boolean('Blacklisted Field', help='Blacklist the Field',compute='_get_blacklisted', inverse='_set_blacklisted')
    
    @api.one
    def _get_blacklisted(self):
        if self.website_form_blacklisted_register:
            return True
        return bool(self.search([('model_id', '=', self.model_id.id), ('name', '=', self.name), ('website_form_blacklisted_register', '=', True)], limit=1))

    @api.one
    def _set_blacklisted(self):
        self.search([('model_id', '=', self.model_id.id), ('name', '=', self.name)]).write({'website_form_blacklisted_register': True});

  
