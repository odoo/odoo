# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools


class ResIdentity(models.Model):
    _name = 'res.identity'
    _description = 'Identity'
    _order = 'id desc'

    # description
    name = fields.Char(string='Name')
    active = fields.Boolean(string='Active', default=True)
    avatar = fields.Image(string='Avatar', max_width=512, max_height=512)
    # contact
    email = fields.Char(string='Email')
    email_formatted = fields.Char(string='Formatted Email', compute="_compute_email_formatted", store=False)
    email_normalized = fields.Char(string='Normalized Email', compute="_compute_email_normalized", store=True)
    phone = fields.Char(string='Phone')
    # link with other contact models
    partner_id = fields.Many2one('res.partner', string='Partner')
    partner_ids = fields.One2many('res.partner', 'identity_id', 'Partners')
    user_id = fields.Many2one('res.users', string='User')
    user_ids = fields.One2many('res.users', 'identity_id', 'Users')
    # security / access
    token = fields.Char(string='Token')

    @api.depends('name', 'email_normalized', 'email')
    def _compute_email_formatted(self):
        for identity in self:
            if identity.email_normalized:
                identity.email_formatted = tools.formataddr((identity.name or identity.email_normalized, identity.email_normalized))
            elif identity.email:
                identity.email_formatted = tools.formataddr((identity.name or '', identity.email))
            else:
                identity.email_formatted = ''

    @api.depends('email')
    def _compute_email_normalized(self):
        for identity in self:
            identity.email_normalized = tools.email_normalize(identity.email) if identity.email else False

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    @api.model
    def name_create(self, name):
        """ Try to find email information from name. """
        identity = self.create(self._identity_get_create_values_from_emails([name]))
        return identity.name_get()[0]

    # ------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------

    def _identity_parse_email(self, email):
        """ Parse identity name (given by text) in order to find a name and an
        email. Supported syntax:

          * Raoul <raoul@grosbedon.fr>
          * "Raoul le Grand" <raoul@grosbedon.fr>
          * Raoul raoul@grosbedon.fr (strange fault tolerant support from df40926d2a57c101a3e2d221ecfd08fbb4fea30e)

        Otherwise: default, everything is set as the name. Starting from 13.3
        returned email will be normalized to have a coherent encoding.
         """
        parsed_name, parsed_email = '', ''
        split_results = tools.email_split_tuples(email)
        if split_results:
            parsed_name, parsed_email = split_results[0]

        if parsed_email and not parsed_name:
            fallback_emails = tools.email_split(email.replace(' ', ','))
            if fallback_emails:
                parsed_email = fallback_emails[0]
                parsed_name = email[:email.index(email)].replace('"', '').replace('<', '').strip()

        if parsed_email:
            parsed_email = tools.email_normalize(parsed_email)
        else:
            parsed_name, parsed_email = email, ''

        return parsed_name, parsed_email

    def _identity_get_create_values_from_emails(self, emails):
        """ Parse a list of text-emails in order to extract a name and an email
        to give to a create.

        :param emails: a list of emails

        :return list: list of dict to use in Identity.create() """
        create_values = []
        for email in emails:
            parsed_name, parsed_email = self._identity_parse_email(email)
            if not parsed_email:
                parsed_email = self.default_get(['email']).get('email')
            if not parsed_name:
                parsed_name = self.default_get(['name']).get('name')

            create_values.append({
                'name': parsed_name or parsed_email,
                'email': parsed_email,
            })

        return create_values

    def _identity_find_or_create_from_email(self, email):
        """ Find or create an identity based on a string holding an email.

        :param str email: string hopefully holding an email. It is parsed to
          try to find an email. If not it is used to populate an identity
          name.
        :return: recordset of identity: either the one matching ``email``
          either a new one creted from ``email`` either void if ``email`` is
          void.
        """
        if not email:
            return self

        parsed_name, parsed_email = self._identity_parse_email(email)
        if not parsed_email:
            parsed_email = self.default_get(['email'])['email']
        if not parsed_name:
            parsed_name = self.default_get(['name'])['name']
        related_partner = self.env['res.partner']

        if parsed_email:
            email_normalized = tools.email_normalize(parsed_email)
            if email_normalized:
                identity = self.search([('email_normalized', '=', email_normalized)], limit=1)
                if identity:
                    return identity
                related_partner = self.env['res.partner'].search([('email_normalized', '=', email_normalized)], limit=1)

        identity_values = {
            'name': parsed_name or parsed_email,
            'email': parsed_email,
            'partner_id': related_partner.id,
        }

        return self.create(identity_values)
