# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import re
import pytz

from odoo import api, fields, models, tools, _
from odoo.osv.expression import get_unaccent_wrapper
from odoo.exceptions import UserError, ValidationError

# put POSIX 'Etc/*' entries at the end to avoid confusing users - see bug 1086728
_tzs = [(tz, tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]
def _tz_get(self):
    return _tzs

@api.model
def _lang_get(self):
    return self.env['res.lang'].get_installed()


class Partner(models.Model):
    _name = "res.partner"
    _description = 'Contact'
    _order = "display_name"

    name = fields.Char(index=True)
    display_name = fields.Char(compute='_compute_display_name', store=True, index=True)
    lang = fields.Selection(
        _lang_get, string='Language',
        help="All the emails and documents sent to this contact will be translated in this language.")
    active_lang_count = fields.Integer(compute='_compute_active_lang_count')
    active = fields.Boolean(default=True)
    type = fields.Selection(
        [('contact', 'Contact'),
         ("private", "Private Address")], string='Address Type', default='contact')
    email = fields.Char()
    email_formatted = fields.Char(
        'Formatted Email', compute='_compute_email_formatted',
        help='Format email address "Name <email@domain>"')
    company_id = fields.Many2one('res.company', 'Company', index=True)
    user_ids = fields.One2many('res.users', 'partner_id', string='Users', auto_join=True)
    partner_share = fields.Boolean(
        'Share Partner', compute='_compute_partner_share', store=True,
        help="Either customer (not a user), either shared user. Indicated the current partner is a customer without "
             "access or with a limited access created for sharing data.")
    tz = fields.Selection(
        _tz_get, string='Timezone', default=lambda self: self._context.get('tz'),
        help="When printing documents and exporting/importing data, time values are computed according to this timezone.\n"
             "If the timezone is not set, UTC (Coordinated Universal Time) is used.\n"
             "Anywhere else, time values are computed according to the time offset of your web client.")
    tz_offset = fields.Char(compute='_compute_tz_offset', string='Timezone offset', invisible=True)

    # hack to allow using plain browse record in qweb views, and used in ir.qweb.field.contact
    self = fields.Many2one(comodel_name=_name, compute='_compute_get_ids')

    _sql_constraints = [
        ('check_name', "CHECK( (type='contact' AND name IS NOT NULL) or (type!='contact') )", 'Contacts require a name'),
    ]

    @api.depends('name')
    def _compute_display_name(self):
        names = dict(self.with_context(show_email=None).name_get())
        for partner in self:
            partner.display_name = names.get(partner.id)

    @api.depends('tz')
    def _compute_tz_offset(self):
        for partner in self:
            partner.tz_offset = datetime.datetime.now(pytz.timezone(partner.tz or 'GMT')).strftime('%z')

    @api.depends('user_ids.share', 'user_ids.active')
    def _compute_partner_share(self):
        for partner in self:
            partner.partner_share = not partner.user_ids or not any(not user.share for user in partner.user_ids)

    def _compute_get_ids(self):
        for partner in self:
            partner.self = partner.id

    @api.depends('lang')
    def _compute_active_lang_count(self):
        lang_count = len(self.env['res.lang'].get_installed())
        for partner in self:
            partner.active_lang_count = lang_count

    @api.model
    def _fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        if (not view_id) and (view_type == 'form') and self._context.get('force_email'):
            view_id = self.env.ref('base.view_partner_simple_form').id
        return super(Partner, self)._fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

    def copy(self, default=None):
        self.ensure_one()
        chosen_name = default.get('name') if default else ''
        new_name = chosen_name or _('%s (copy)') % self.name
        default = dict(default or {}, name=new_name)
        return super(Partner, self).copy(default)

    @api.depends('name', 'email')
    def _compute_email_formatted(self):
        for partner in self:
            if partner.email:
                partner.email_formatted = tools.formataddr((partner.name or u"False", partner.email or u"False"))
            else:
                partner.email_formatted = ''

    # YTI TO CHECK IF SHOULD MOVE
    def _update_fields_values(self, fields):
        """ Returns dict of write() values for synchronizing ``fields`` """
        values = {}
        for fname in fields:
            field = self._fields[fname]
            if field.type == 'many2one':
                values[fname] = self[fname].id
            elif field.type == 'one2many':
                raise AssertionError(_('One2Many fields cannot be synchronized as part of `commercial_fields` or `address fields`'))
            elif field.type == 'many2many':
                values[fname] = [(6, 0, self[fname].ids)]
            else:
                values[fname] = self[fname]
        return values

    def write(self, vals):
        if vals.get('active') is False:
            # DLE: It should not be necessary to modify this to make work the ORM. The problem was just the recompute
            # of partner.user_ids when you create a new user for this partner, see test test_70_archive_internal_partners
            # You modified it in a previous commit, see original commit of this:
            # https://github.com/odoo/odoo/commit/9d7226371730e73c296bcc68eb1f856f82b0b4ed
            #
            # RCO: when creating a user for partner, the user is automatically added in partner.user_ids.
            # This is wrong if the user is not active, as partner.user_ids only returns active users.
            # Hence this temporary hack until the ORM updates inverse fields correctly.
            self.invalidate_cache(['user_ids'], self._ids)
            for partner in self:
                if partner.active and partner.user_ids:
                    raise ValidationError(_('You cannot archive a contact linked to an internal user.'))
        # res.partner must only allow to set the company_id of a partner if it
        # is the same as the company of all users that inherit from this partner
        # (this is to allow the code from res_users to write to the partner!) or
        # if setting the company_id to False (this is compatible with any user
        # company)
        if vals.get('parent_id'):
            vals['company_name'] = False
        if vals.get('company_id'):
            company = self.env['res.company'].browse(vals['company_id'])
            for partner in self.filtered(lambda p: p.user_ids):
                companies = set(user.company_id for user in partner.user_ids)
                if len(companies) > 1 or company not in companies:
                    raise UserError(
                        ("The selected company is not compatible with the companies of the related user(s)"))
        result = True
        # To write in SUPERUSER on field is_company and avoid access rights problems.
        if 'is_company' in vals and self.user_has_groups('base.group_partner_manager') and not self.env.su:
            result = super(Partner, self.sudo()).write({'is_company': vals.get('is_company')})
            del vals['is_company']
        result = result and super(Partner, self).write(vals)
        for partner in self:
            if any(u.has_group('base.group_user') for u in partner.user_ids if u != self.env.user):
                self.env['res.users'].check_access_rights('write')
        return result

    def _parse_partner_name(self, text):
        """ Parse partner name (given by text) in order to find a name and an
        email. Supported syntax:

          * Raoul <raoul@grosbedon.fr>
          * "Raoul le Grand" <raoul@grosbedon.fr>
          * Raoul raoul@grosbedon.fr (strange fault tolerant support from df40926d2a57c101a3e2d221ecfd08fbb4fea30e)

        Otherwise: default, everything is set as the name. Starting from 13.3
        returned email will be normalized to have a coherent encoding.
         """
        name, email = '', ''
        split_results = tools.email_split_tuples(text)
        if split_results:
            name, email = split_results[0]

        if email and not name:
            fallback_emails = tools.email_split(text.replace(' ', ','))
            if fallback_emails:
                email = fallback_emails[0]
                name = text[:text.index(email)].replace('"', '').replace('<', '').strip()

        if email:
            email = tools.email_normalize(email)
        else:
            name, email = text, ''

        return name, email

    @api.model
    def name_create(self, name):
        """ Override of orm's name_create method for partners. The purpose is
            to handle some basic formats to create partners using the
            name_create.
            If only an email address is received and that the regex cannot find
            a name, the name will have the email value.
            If 'force_email' key in context: must find the email address. """
        name, email = self._parse_partner_name(name)
        if self._context.get('force_email') and not email:
            raise UserError(_("Couldn't create contact without email address!"))

        create_values = {self._rec_name: name or email}
        if email:  # keep default_email in context
            create_values['email'] = email
        partner = self.create(create_values)
        return partner.name_get()[0]

    def _get_name(self):
        """ Utility method to allow name_get to be overrided without re-browse the partner """
        partner = self
        name = partner.name or ''
        if self._context.get('show_email') and partner.email:
            name = "%s <%s>" % (name, partner.email)
        return name

    def name_get(self):
        res = []
        for partner in self:
            name = partner._get_name()
            res.append((partner.id, name))
        return res

    def _get_name_search_order_by_fields(self):
        return ''

    @api.model
    def _name_search_where(self):
        # Overridden in partner module to add ref/vat fields
        return ""

    @api.model
    def _name_search_query_vals(self):
        unaccent = get_unaccent_wrapper(self.env.cr)
        return {
            'email': unaccent('res_partner.email'),
            'display_name': unaccent('res_partner.display_name'),
            'percent': unaccent('%s'),
        }

    @api.model
    def _name_search_where_clause_params(self, search_name):
        res = [search_name] * 2  # for email / display_name
        res += [search_name]  # for order by
        return res

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        self = self.with_user(name_get_uid or self.env.uid)
        # as the implementation is in SQL, we force the recompute of fields if necessary
        self.recompute(['display_name'])
        self.flush()
        if args is None:
            args = []
        order_by_rank = self.env.context.get('res_partner_search_mode') 
        if (name or order_by_rank) and operator in ('=', 'ilike', '=ilike', 'like', '=like'):
            self.check_access_rights('read')
            where_query = self._where_calc(args)
            self._apply_ir_rules(where_query, 'read')
            from_clause, where_clause, where_clause_params = where_query.get_sql()
            from_str = from_clause if from_clause else 'res_partner'
            where_str = where_clause and (" WHERE %s AND " % where_clause) or ' WHERE '

            # search on the name of the contacts and of its company
            search_name = name
            if operator in ('ilike', 'like'):
                search_name = '%%%s%%' % name
            if operator in ('=ilike', '=like'):
                operator = operator[1:]

            fields = self._get_name_search_order_by_fields()

            query = """SELECT res_partner.id
                       FROM {from_str}
                       {where} ({email} {operator} {percent}
                       OR {display_name} {operator} {percent}
                       %s)
                       ORDER BY {fields} {display_name} {operator} {percent} desc, 
                            {display_name}
                    """ % (self._name_search_where())
            query_vals = {
                'from_str': from_str,
                'fields': fields,
                'where': where_str,
                'operator': operator,
            }
            query_vals.update(self._name_search_query_vals())
            query = query.format(**query_vals)

            where_clause_params += self._name_search_where_clause_params(search_name)
            if limit:
                query += ' limit %s'
                where_clause_params.append(limit)
            print('caca', query, where_clause_params)
            self.env.cr.execute(query, where_clause_params)
            partner_ids = [row[0] for row in self.env.cr.fetchall()]

            if partner_ids:
                return models.lazy_name_get(self.browse(partner_ids))
            else:
                return []
        return super(Partner, self)._name_search(name, args, operator=operator, limit=limit, name_get_uid=name_get_uid)

    @api.model
    def find_or_create(self, email, assert_valid_email=False):
        """ Find a partner with the given ``email`` or use :py:method:`~.name_create`
        to create a new one.

        :param str email: email-like string, which should contain at least one email,
            e.g. ``"Raoul Grosbedon <r.g@grosbedon.fr>"``
        :param boolean assert_valid_email: raise if no valid email is found
        :return: newly created record
        """
        if not email:
            raise ValueError(_('An email is required for find_or_create to work'))

        parsed_name, parsed_email = self._parse_partner_name(email)
        if not parsed_email and assert_valid_email:
            raise ValueError(_('A valid email is required for find_or_create to work properly.'))

        partners = self.search([('email', '=ilike', parsed_email)], limit=1)
        if partners:
            return partners

        create_values = {self._rec_name: parsed_name or parsed_email}
        if parsed_email:  # keep default_email in context
            create_values['email'] = parsed_email
        return self.create(create_values)

    def _email_send(self, email_from, subject, body, on_error=None):
        for partner in self.filtered('email'):
            tools.email_send(email_from, [partner.email], subject, body, on_error)
        return True

    def address_get(self, adr_pref=None):
        """ Find contacts/addresses of the right type(s) by doing a depth-first-search
        through descendants within company boundaries (stop at entities flagged ``is_company``)
        then continuing the search at the ancestors that are within the same company boundaries.
        Defaults to partners of type ``'default'`` when the exact type is not found, or to the
        provided partner itself if no type ``'default'`` is found either. """
        adr_pref = set(adr_pref or [])
        if 'contact' not in adr_pref:
            adr_pref.add('contact')
        result = {}
        visited = set()
        for partner in self:
            current_partner = partner
            while current_partner:
                to_scan = [current_partner]
                # Scan descendants, DFS
                while to_scan:
                    record = to_scan.pop(0)
                    visited.add(record)
                    if record.type in adr_pref and not result.get(record.type):
                        result[record.type] = record.id
                    if len(result) == len(adr_pref):
                        return result
                    to_scan = [c for c in record.child_ids
                                 if c not in visited
                                 if not c.is_company] + to_scan

                # Continue scanning at ancestor if current_partner is not a commercial entity
                if current_partner.is_company or not current_partner.parent_id:
                    break
                current_partner = current_partner.parent_id

        # default to type 'contact' or the partner itself
        default = result.get('contact', self.id or False)
        for adr_type in adr_pref:
            result[adr_type] = result.get(adr_type) or default
        return result
