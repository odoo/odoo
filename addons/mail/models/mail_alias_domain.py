# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, exceptions, fields, models, _
from odoo.addons.mail.models.mail_alias import dot_atom_text


class AliasDomain(models.Model):
    """ Model alias domains, now company-specific. Alias domains are email
    domains used to receive emails through catchall and bounce aliases, as
    well as using mail.alias records to redirect email replies.

    This replaces ``mail.alias.domain`` configuration parameter use until v16.
    """
    _name = 'mail.alias.domain'
    _description = "Email Domain"
    _order = 'sequence ASC, id ASC'

    name = fields.Char(
        'Name', required=True,
        help="Email domain e.g. 'example.com' in 'odoo@example.com'")
    company_ids = fields.One2many(
        'res.company', 'alias_domain_id', string='Companies',
        help="Companies using this domain as default for sending mails")
    sequence = fields.Integer(default=10)
    bounce_alias = fields.Char(
        'Bounce Alias', default='bounce', required=True,
        help="Local-part of email used for Return-Path used when emails bounce e.g. "
             "'bounce' in 'bounce@example.com'")
    bounce_email = fields.Char('Bounce Email', compute='_compute_bounce_email')
    catchall_alias = fields.Char(
        'Catchall Alias', default='catchall', required=True,
        help="Local-part of email used for Reply-To to catch answers e.g. "
             "'catchall' in 'catchall@example.com'")
    catchall_email = fields.Char('Catchall Email', compute='_compute_catchall_email')
    default_from = fields.Char(
        'Default From Alias', default='notifications',
        help="Default from when it does not match outgoing server filters. Can be either "
             "a local-part e.g. 'notifications' either a complete email address e.g. "
             "'notifications@example.com' to override all outgoing emails.")
    default_from_email = fields.Char('Default From', compute='_compute_default_from_email')

    _sql_constraints = [
        (
            'bounce_email_uniques',
            'UNIQUE(bounce_alias, name)',
            'Bounce emails should be unique'
        ),
        (
            'catchall_email_uniques',
            'UNIQUE(catchall_alias, name)',
            'Catchall emails should be unique'
        ),
    ]

    @api.depends('bounce_alias', 'name')
    def _compute_bounce_email(self):
        self.bounce_email = ''
        for domain in self.filtered('bounce_alias'):
            domain.bounce_email = f'{domain.bounce_alias}@{domain.name}'

    @api.depends('catchall_alias', 'name')
    def _compute_catchall_email(self):
        self.catchall_email = ''
        for domain in self.filtered('catchall_alias'):
            domain.catchall_email = f'{domain.catchall_alias}@{domain.name}'

    @api.depends('default_from', 'name')
    def _compute_default_from_email(self):
        """ Default from may be a valid complete email and not only a left-part
        like bounce or catchall aliases. Adding domain name should therefore
        be done only if necessary. """
        self.default_from_email = ''
        for domain in self.filtered('default_from'):
            if "@" in domain.default_from:
                domain.default_from_email = domain.default_from
            else:
                domain.default_from_email = f'{domain.default_from}@{domain.name}'

    @api.constrains('bounce_alias', 'catchall_alias')
    def _check_bounce_catchall_uniqueness(self):
        names = self.filtered('bounce_alias').mapped('bounce_alias') + self.filtered('catchall_alias').mapped('catchall_alias')
        if not names:
            return

        similar_domains = self.env['mail.alias.domain'].search([('name', 'in', self.mapped('name'))])
        for tocheck in self:
            if any(similar.bounce_alias == tocheck.bounce_alias
                   for similar in similar_domains if similar != tocheck and similar.name == tocheck.name):
                raise exceptions.ValidationError(
                    _('Bounce alias %(bounce)s is already used for another domain with same name. '
                      'Use another bounce or simply use the other alias domain.',
                      bounce=tocheck.bounce_email)
                )
            if any(similar.catchall_alias == tocheck.catchall_alias
                   for similar in similar_domains if similar != tocheck and similar.name == tocheck.name):
                raise exceptions.ValidationError(
                    _('Catchall alias %(catchall)s is already used for another domain with same name. '
                      'Use another catchall or simply use the other alias domain.',
                      catchall=tocheck.catchall_email)
                )

        # search on left-part only to speedup, then filter on right part
        potential_aliases = self.env['mail.alias'].search([
            ('alias_name', 'in', list(set(names))),
            ('alias_domain_id', '!=', False)
        ])
        existing = next(
            (alias for alias in potential_aliases
             if alias.display_name in (self.mapped('bounce_email') + self.mapped('catchall_email'))),
            self.env['mail.alias']
        )
        if existing:
            document_name = False
            # If owner or target: display document name also in the warning
            if existing.alias_parent_model_id and existing.alias_parent_thread_id:
                document_name = self.env[existing.alias_parent_model_id.model].sudo().browse(existing.alias_parent_thread_id).display_name
            elif existing.alias_model_id and existing.alias_force_thread_id:
                document_name = self.env[existing.alias_model_id.model].sudo().browse(existing.alias_force_thread_id).display_name
            if document_name:
                raise exceptions.ValidationError(
                    _("Bounce/Catchall '%(matching_alias_name)s' is already used by %(document_name)s. Choose another alias or change it on the other document.",
                      matching_alias_name=existing.display_name,
                      document_name=document_name)
                        )
            raise exceptions.ValidationError(
                _("Bounce/Catchall '%(matching_alias_name)s' is already used. Choose another alias or change it on the linked model.",
                  matching_alias_name=existing.display_name)
            )

    @api.constrains('name')
    def _check_name(self):
        """ Should match a sanitized version of itself, otherwise raise to warn
        user (do not dynamically change it, would be confusing). """
        for domain in self:
            if not dot_atom_text.match(domain.name):
                raise exceptions.ValidationError(
                    _("You cannot use anything else than unaccented latin characters in the domain name %(domain_name)s.",
                      domain_name=domain.name)
                )

    @api.model_create_multi
    def create(self, vals_list):
        """ Sanitize bounce_alias / catchall_alias / default_from """
        for vals in vals_list:
            self._sanitize_configuration(vals)

        alias_domains = super().create(vals_list)

        # alias domain init: populate companies and aliases at first creation
        if alias_domains and self.search_count([]) == len(alias_domains):
            # during first init we assume that we want to attribute this
            # alias domain to all companies, irrespective of the fact
            # that they are archived or not. So we run active_test=False
            # on the just created alias domain

            self.env['res.company'].with_context(active_test=False).search(
                [('alias_domain_id', '=', False)]
            ).alias_domain_id = alias_domains[0].id
            self.env['mail.alias'].sudo().search(
                [('alias_domain_id', '=', False)]
            ).alias_domain_id = alias_domains[0].id

        return alias_domains

    def write(self, vals):
        """ Sanitize bounce_alias / catchall_alias / default_from """
        self._sanitize_configuration(vals)
        return super().write(vals)

    @api.model
    def _sanitize_configuration(self, config_values):
        """ Tool sanitizing configuration values for domains """
        if config_values.get('bounce_alias'):
            config_values['bounce_alias'] = self.env['mail.alias']._sanitize_alias_name(config_values['bounce_alias'])
        if config_values.get('catchall_alias'):
            config_values['catchall_alias'] = self.env['mail.alias']._sanitize_alias_name(config_values['catchall_alias'])
        if config_values.get('default_from'):
            config_values['default_from'] = self.env['mail.alias']._sanitize_alias_name(
                config_values['default_from'], is_email=True
            )
        return config_values

    @api.model
    def _migrate_icp_to_domain(self):
        """ Compatibility layer helping going from pre-v17 ICP to alias
        domains. Mainly used when base mail configuration is done with 'base'
        module only and 'mail' is installed afterwards: configuration should
        not be lost (odoo.sh use case). """
        Icp = self.env['ir.config_parameter'].sudo()
        alias_domain = Icp.get_param('mail.catchall.domain')
        if alias_domain:
            existing = self.search([('name', '=', alias_domain)])
            if existing:
                return existing
            bounce_alias = Icp.get_param('mail.bounce.alias')
            catchall_alias = Icp.get_param('mail.catchall.alias')
            default_from = Icp.get_param('mail.default.from')
            return self.create({
                'bounce_alias': bounce_alias or 'bounce',
                'catchall_alias': catchall_alias or 'catchall',
                'default_from': default_from or 'notifications',
                'name': alias_domain,
            })
        return self.browse()
