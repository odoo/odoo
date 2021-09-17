# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, exceptions, fields, models, _


class AliasDomain(models.Model):
    """ Model alias domains, now company-specific. Alias domains are email
    domains used to receive emails through catchall and bounce aliases, as
    well as using mail.alias records to redirect email replies.

    This replaces ``mail.alias.domain`` configuration parameter use until v16.
    """
    _name = 'mail.alias.domain'
    _description = "Email Domain"
    _order = 'sequence ASC, id DESC'
    _rec_name = 'name'

    name = fields.Char('Name', required=True)
    company_ids = fields.Many2many('res.company', string='Used in')
    sequence = fields.Integer(default=10)
    bounce = fields.Char('Bounce Alias', default='bounce', required=True)
    catchall = fields.Char('Catchall Alias', default='catchall', required=True)

    _sql_constraints = [
        (
            'code_company_uniq',
            'UNIQUE(name)',
            'Alias domain name should be unique'
        ),
    ]

    @api.constrains('bounce', 'catchall')
    def _check_bounce_uniqueness(self):
        names = self.filtered('bounce').mapped('bounce') + self.filtered('catchall').mapped('catchall')
        if not names:
            return

        existing = self.env['mail.alias'].search(
            [('alias_name', 'in', list(set(names)))],
            limit=1,
        )
        if existing.alias_parent_model_id and existing.alias_parent_thread_id:
            # If parent model and parent thread ID both are set, display document name also in the warning
            document_name = self.env[existing.alias_parent_model_id.model].sudo().browse(existing.alias_parent_thread_id).display_name
            raise exceptions.ValidationError(
                _("'%(matching_alias_name)s' is already used by the %(document_name)s %(model_name)s. Choose another alias or change it on the other document.",
                  matching_alias_name=existing.display_name,
                  document_name=document_name,
                  model_name=existing.alias_parent_model_id.name)
                    )
        if existing:
            raise exceptions.ValidationError(
                _("'%(matching_alias_name)s' is already linked with %(alias_model_name)s. Choose another alias or change it on the linked model.",
                  matching_alias_name=existing.display_name,
                  alias_model_name=existing.alias_model_id.name)
            )

    @api.model_create_multi
    def create(self, vals_list):
        """ Sanitize bounce / catchall """
        for vals in vals_list:
            if vals.get('bounce'):
                vals['bounce'] = self.env['mail.alias']._sanitize_alias_name(vals['bounce'])
            if vals.get('catchall'):
                vals['catchall'] = self.env['mail.alias']._sanitize_alias_name(vals['catchall'])
        return super().create(vals_list)

    def write(self, vals):
        """ Sanitize bounce / catchall """
        if vals.get('bounce'):
            vals['bounce'] = self.env['mail.alias']._sanitize_alias_name(vals['bounce'])
        if vals.get('catchall'):
            vals['catchall'] = self.env['mail.alias']._sanitize_alias_name(vals['catchall'])
        return super().write(vals)
