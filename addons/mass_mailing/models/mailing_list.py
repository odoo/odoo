# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import _, api, Command, fields, models, tools
from odoo.exceptions import UserError


class MassMailingList(models.Model):
    """Model of a contact list. """
    _name = 'mailing.list'
    _order = 'name'
    _description = 'Mailing List'
    _mailing_enabled = True
    _order = 'create_date DESC'
    # As this model has their own data merge, avoid to enable the generic data_merge on that model.
    _disable_data_merge = True

    name = fields.Char(string='Mailing List', required=True)
    active = fields.Boolean(default=True)
    contact_count = fields.Integer(compute="_compute_mailing_list_statistics", string='Number of Contacts')
    contact_count_email = fields.Integer(compute="_compute_mailing_list_statistics", string="Number of Emails")
    contact_count_opt_out = fields.Integer(compute="_compute_mailing_list_statistics", string="Number of Opted-out")
    contact_pct_opt_out = fields.Float(compute="_compute_mailing_list_statistics", string="Percentage of Opted-out")
    contact_count_blacklisted = fields.Integer(compute="_compute_mailing_list_statistics", string="Number of Blacklisted")
    contact_pct_blacklisted = fields.Float(compute="_compute_mailing_list_statistics", string="Percentage of Blacklisted")
    contact_pct_bounce = fields.Float(compute="_compute_mailing_list_statistics", string="Percentage of Bouncing")
    contact_ids = fields.Many2many(
        'mailing.contact', 'mailing_subscription', 'list_id', 'contact_id',
        string='Mailing Lists', copy=False)
    mailing_count = fields.Integer(compute="_compute_mailing_count", string="Number of Mailing")
    mailing_ids = fields.Many2many(
        'mailing.mailing', 'mail_mass_mailing_list_rel',
        string='Mass Mailings', copy=False)
    subscription_ids = fields.One2many(
        'mailing.subscription', 'list_id',
        string='Subscription Information',
        copy=True, depends=['contact_ids'])
    is_public = fields.Boolean(
        string='Show In Preferences', default=False,
        help='The mailing list can be accessible by recipients in the subscription '
             'management page to allow them to update their preferences.')

    # ------------------------------------------------------
    # COMPUTE / ONCHANGE
    # ------------------------------------------------------

    @api.depends('mailing_ids')
    def _compute_mailing_count(self):
        data = {}
        if self.ids:
            self.env.cr.execute('''
                SELECT mailing_list_id, count(*)
                FROM mail_mass_mailing_list_rel
                WHERE mailing_list_id IN %s
                GROUP BY mailing_list_id''', (tuple(self.ids),))
            data = dict(self.env.cr.fetchall())
        for mailing_list in self:
            mailing_list.mailing_count = data.get(mailing_list._origin.id, 0)

    @api.depends('contact_ids')
    def _compute_mailing_list_statistics(self):
        """ Computes various statistics for this mailing.list that allow users
        to have a global idea of its quality (based on blacklist, opt-outs, ...).

        As some fields depend on the value of each other (mainly percentages),
        we compute everything in a single method. """
        # flush, notably to have email_normalized computed on contact model
        self.env.flush_all()

        # 1. Fetch contact data and associated counts (total / blacklist / opt-out)
        contact_statistics_per_mailing = self._fetch_contact_statistics()

        # 2. Fetch bounce data
        # Optimized SQL way of fetching the count of contacts that have
        # at least 1 message bouncing for passed mailing.lists """
        bounce_per_mailing = {}
        if self.ids:
            sql = '''
                SELECT list_sub.list_id, COUNT(DISTINCT mc.id)
                FROM mailing_contact mc
                LEFT OUTER JOIN mailing_subscription list_sub
                ON mc.id = list_sub.contact_id
                WHERE mc.message_bounce > 0
                AND list_sub.list_id in %s
                GROUP BY list_sub.list_id
            '''
            self.env.cr.execute(sql, (tuple(self.ids),))
            bounce_per_mailing = dict(self.env.cr.fetchall())

        # 3. Compute and assign all counts / pct fields
        for mailing_list in self:
            contact_counts = contact_statistics_per_mailing.get(mailing_list.id, {})
            for field, value in contact_counts.items():
                if field in self._fields:
                    mailing_list[field] = value

            if mailing_list.contact_count != 0:
                mailing_list.contact_pct_opt_out = 100 * (mailing_list.contact_count_opt_out / mailing_list.contact_count)
                mailing_list.contact_pct_blacklisted = 100 * (mailing_list.contact_count_blacklisted / mailing_list.contact_count)
                mailing_list.contact_pct_bounce = 100 * (bounce_per_mailing.get(mailing_list.id, 0) / mailing_list.contact_count)
            else:
                mailing_list.contact_pct_opt_out = 0
                mailing_list.contact_pct_blacklisted = 0
                mailing_list.contact_pct_bounce = 0

    # ------------------------------------------------------
    # ORM overrides
    # ------------------------------------------------------

    def write(self, vals):
        # Prevent archiving used mailing list
        if 'active' in vals and not vals.get('active'):
            mass_mailings = self.env['mailing.mailing'].search_count([
                ('state', '!=', 'done'),
                ('contact_list_ids', 'in', self.ids),
            ])

            if mass_mailings > 0:
                raise UserError(_("At least one of the mailing list you are trying to archive is used in an ongoing mailing campaign."))

        return super(MassMailingList, self).write(vals)

    @api.depends('contact_count')
    def _compute_display_name(self):
        for mailing_list in self:
            mailing_list.display_name = f"{mailing_list.name} ({mailing_list.contact_count})"

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [dict(vals, name=self.env._("%s (copy)", mailing_list.name)) for mailing_list, vals in zip(self, vals_list)]

    # ------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------

    def action_open_import(self):
        """Open the mailing list contact import wizard."""
        action = self.env['ir.actions.actions']._for_xml_id('mass_mailing.mailing_contact_import_action')
        action['context'] = {
            **self.env.context,
            'default_mailing_list_ids': self.ids,
            'default_subscription_ids': [
                Command.create({'list_id': mailing_list.id})
                for mailing_list in self
            ],
        }
        return action

    def action_send_mailing(self):
        """Open the mailing form view, with the current lists set as recipients."""
        action = self.env["ir.actions.actions"]._for_xml_id('mass_mailing.mailing_mailing_action_mail')

        action.update({
            'context': {
                **self.env.context,
                'default_contact_list_ids': self.ids,
                'default_mailing_type': 'mail',
                'default_model_id': self.env['ir.model']._get_id('mailing.list'),
            },
            'target': 'current',
            'view_type': 'form',
        })

        return action

    def action_view_contacts(self):
        action = self.env["ir.actions.actions"]._for_xml_id("mass_mailing.action_view_mass_mailing_contacts")
        action['domain'] = [('list_ids', 'in', self.ids)]
        action['context'] = {'default_list_ids': self.ids}
        return action

    def action_view_contacts_email(self):
        action = self.action_view_contacts()
        action['context'] = dict(action.get('context', {}), search_default_filter_valid_email_recipient=1)
        return action

    def action_view_mailings(self):
        action = self.env["ir.actions.actions"]._for_xml_id('mass_mailing.mailing_mailing_action_mail')
        action['domain'] = [('contact_list_ids', 'in', self.ids)]
        action['context'] = {'default_mailing_type': 'mail', 'default_contact_list_ids': self.ids}
        return action

    def action_view_contacts_opt_out(self):
        action = self.env["ir.actions.actions"]._for_xml_id('mass_mailing.action_view_mass_mailing_contacts')
        action['domain'] = [('list_ids', 'in', self.id)]
        action['context'] = {'default_list_ids': self.ids, 'create': False, 'search_default_filter_opt_out': 1}
        return action

    def action_view_contacts_blacklisted(self):
        action = self.env["ir.actions.actions"]._for_xml_id('mass_mailing.action_view_mass_mailing_contacts')
        action['domain'] = [('list_ids', 'in', self.id)]
        action['context'] = {'default_list_ids': self.ids, 'create': False, 'search_default_filter_blacklisted': 1}
        return action

    def action_view_contacts_bouncing(self):
        action = self.env["ir.actions.actions"]._for_xml_id('mass_mailing.action_view_mass_mailing_contacts')
        action['domain'] = [('list_ids', 'in', self.id)]
        action['context'] = {'default_list_ids': self.ids, 'create': False, 'search_default_filter_bounce': 1}
        return action

    def action_merge(self, src_lists, archive):
        """
            Insert all the contact from the mailing lists 'src_lists' to the
            mailing list in 'self'. Possibility to archive the mailing lists
            'src_lists' after the merge except the destination mailing list 'self'.
        """
        # Explanation of the SQL query with an example. There are the following lists
        # A (id=4): yti@odoo.com; yti@example.com
        # B (id=5): yti@odoo.com; yti@openerp.com
        # C (id=6): nothing
        # To merge the mailing lists A and B into C, we build the view st that looks
        # like this with our example:
        #
        #  contact_id |           email           | row_number |  list_id |
        # ------------+---------------------------+------------------------
        #           4 | yti@odoo.com              |          1 |        4 |
        #           6 | yti@odoo.com              |          2 |        5 |
        #           5 | yti@example.com           |          1 |        4 |
        #           7 | yti@openerp.com           |          1 |        5 |
        #
        # The row_column is kind of an occurrence counter for the email address.
        # Then we create the Many2many relation between the destination list and the contacts
        # while avoiding to insert an existing email address (if the destination is in the source
        # for example)
        self.ensure_one()
        # Put destination is sources lists if not already the case
        src_lists |= self
        self.env.flush_all()
        self.env.cr.execute("""
            INSERT INTO mailing_subscription (contact_id, list_id)
            SELECT st.contact_id AS contact_id, %s AS list_id
            FROM
                (
                SELECT
                    contact.id AS contact_id,
                    contact.email AS email,
                    list.id AS list_id,
                    row_number() OVER (PARTITION BY email ORDER BY email) AS rn
                FROM
                    mailing_contact contact,
                    mailing_subscription contact_list_rel,
                    mailing_list list
                WHERE contact.id=contact_list_rel.contact_id
                AND COALESCE(contact_list_rel.opt_out,FALSE) = FALSE
                AND contact.email_normalized NOT IN (select email from mail_blacklist where active = TRUE)
                AND list.id=contact_list_rel.list_id
                AND list.id IN %s
                AND NOT EXISTS
                    (
                    SELECT 1
                    FROM
                        mailing_contact contact2,
                        mailing_subscription contact_list_rel2
                    WHERE contact2.email = contact.email
                    AND contact_list_rel2.contact_id = contact2.id
                    AND contact_list_rel2.list_id = %s
                    )
                ) st
            WHERE st.rn = 1;""", (self.id, tuple(src_lists.ids), self.id))
        self.env.invalidate_all()
        if archive:
            (src_lists - self).action_archive()

    def close_dialog(self):
        return {'type': 'ir.actions.act_window_close'}

    # ------------------------------------------------------
    # SUBSCRIPTION MANAGEMENT
    # ------------------------------------------------------

    def _update_subscription_from_email(self, email, opt_out=True, force_message=None):
        """ When opting-out: we have to switch opted-in subscriptions. We don't
        need to create subscription for other lists as opt-out = not being a
        member.

        When opting-in: we have to switch opted-out subscriptions and create
        subscription for other mailing lists id they are public. Indeed a
        contact is opted-in when being subscribed in a mailing list.

        :param str email: email address that should opt-in or opt-out from
          mailing lists;
        :param boolean opt_out: if True, opt-out from lists given by self if
          'email' is member of it. If False, opt-in in lists givben by self
          and create membership if not already member;
        :param str force_message: if given, post a note using that body on
          contact instead of generated update message. Give False to entirely
          skip the note step;
        """
        email_normalized = tools.email_normalize(email)
        if not self or not email_normalized:
            return

        contacts = self.env['mailing.contact'].with_context(active_test=False).search(
            [('email_normalized', '=', email_normalized)]
        )
        if not contacts:
            return

        # switch opted-in subscriptions
        if opt_out:
            current_opt_in = contacts.subscription_ids.filtered(
                lambda sub: not sub.opt_out and sub.list_id in self
            )
            if current_opt_in:
                current_opt_in.write({'opt_out': True})
        # switch opted-out subscription and create missing subscriptions
        else:
            subscriptions = contacts.subscription_ids.filtered(lambda sub: sub.list_id in self)
            current_opt_out = subscriptions.filtered('opt_out')
            if current_opt_out:
                current_opt_out.write({'opt_out': False})

            # create a subscription (for a single contact) for missing lists
            missing_lists = self - subscriptions.list_id
            if missing_lists:
                self.env['mailing.subscription'].create([
                    {'contact_id': contacts[0].id,
                     'list_id': mailing_list.id}
                    for mailing_list in missing_lists
                ])

        for contact in contacts:
            # do not log if no opt-out / opt-in was actually done
            if opt_out:
                updated = current_opt_in.filtered(lambda sub: sub.contact_id == contact).list_id
            else:
                updated = current_opt_out.filtered(lambda sub: sub.contact_id == contact).list_id + missing_lists
            if not updated:
                continue

            if force_message is False:
                continue
            if force_message:
                body = force_message
            elif opt_out:
                body = Markup('<p>%s</p><ul>%s</ul>') % (
                    _('%(contact_name)s unsubscribed from the following mailing list(s)', contact_name=contact.display_name),
                    Markup().join(Markup('<li>%s</li>') % name for name in updated.mapped('name')),
                )
            else:
                body = Markup('<p>%s</p><ul>%s</ul>') % (
                    _('%(contact_name)s subscribed to the following mailing list(s)', contact_name=contact.display_name),
                    Markup().join(Markup('<li>%s</li>') % name for name in updated.mapped('name')),
                )
            contact.with_context(mail_create_nosubscribe=True).message_post(
                body=body,
                subtype_id=self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note'),
            )

    # ------------------------------------------------------
    # MAILING
    # ------------------------------------------------------

    def _mailing_get_default_domain(self, mailing):
        return [('list_ids', 'in', mailing.contact_list_ids.ids)]

    def _mailing_get_opt_out_list(self, mailing):
        """ Check subscription on all involved mailing lists. If user is opt_out
        on one list but not on another if two users with same email address, one
        opted in and the other one opted out, send the mail anyway. """
        # TODO DBE Fixme : Optimize the following to get real opt_out and opt_in
        subscriptions = self.subscription_ids if self else mailing.contact_list_ids.subscription_ids
        opt_out_contacts = subscriptions.filtered(lambda rel: rel.opt_out).mapped('contact_id.email_normalized')
        opt_in_contacts = subscriptions.filtered(lambda rel: not rel.opt_out).mapped('contact_id.email_normalized')
        opt_out = set(c for c in opt_out_contacts if c not in opt_in_contacts)
        return opt_out

    # ------------------------------------------------------
    # UTILITY
    # ------------------------------------------------------

    def _fetch_contact_statistics(self):
        """ Compute number of contacts matching various conditions.
        (see '_get_contact_count_select_fields' for details)

        Will return a dict under the form:
        {
            42: { # 42 being the mailing list ID
                'contact_count': 52,
                'contact_count_email': 35,
                'contact_count_opt_out': 5,
                'contact_count_blacklisted': 2
            },
            ...
        } """

        res = []
        if self.ids:
            self.env.cr.execute(f'''
                SELECT
                    {','.join(self._get_contact_statistics_fields().values())}
                FROM
                    mailing_subscription r
                    {self._get_contact_statistics_joins()}
                WHERE list_id IN %s
                GROUP BY
                    list_id;
            ''', (tuple(self.ids), ))
            res = self.env.cr.dictfetchall()

        contact_counts = {}
        for res_item in res:
            mailing_list_id = res_item.pop('mailing_list_id')
            contact_counts[mailing_list_id] = res_item

        for mass_mailing in self:
            # adds default 0 values for ids that don't have statistics
            if mass_mailing.id not in contact_counts:
                contact_counts[mass_mailing.id] = {
                    field: 0
                    for field in mass_mailing._get_contact_statistics_fields()
                }

        return contact_counts

    def _get_contact_statistics_fields(self):
        """ Returns fields and SQL query select path in a dictionnary.
        This is done to be easily overridable in subsequent modules.

        - mailing_list_id             id of the associated mailing.list
        - contact_count:              all contacts
        - contact_count_email:        all valid emails
        - contact_count_opt_out:      all opted-out contacts
        - contact_count_blacklisted:  all blacklisted contacts """

        return {
            'mailing_list_id': 'list_id AS mailing_list_id',
            'contact_count': 'COUNT(*) AS contact_count',
            'contact_count_email': '''
                SUM(CASE WHEN
                        (c.email_normalized IS NOT NULL
                        AND COALESCE(r.opt_out,FALSE) = FALSE
                        AND bl.id IS NULL)
                        THEN 1 ELSE 0 END) AS contact_count_email''',
            'contact_count_opt_out': '''
                SUM(CASE WHEN COALESCE(r.opt_out,FALSE) = TRUE
                    THEN 1 ELSE 0 END) AS contact_count_opt_out''',
            'contact_count_blacklisted': '''
                SUM(CASE WHEN bl.id IS NOT NULL
                THEN 1 ELSE 0 END) AS contact_count_blacklisted'''
        }

    def _get_contact_statistics_joins(self):
        """ Extracted to be easily overridable by sub-modules (such as mass_mailing_sms). """
        return """
            LEFT JOIN mailing_contact c ON (r.contact_id=c.id)
            LEFT JOIN mail_blacklist bl on c.email_normalized = bl.email and bl.active"""
