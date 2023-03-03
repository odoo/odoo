# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, Command, fields, models
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
        'mailing.contact', 'mailing_contact_list_rel', 'list_id', 'contact_id',
        string='Mailing Lists', copy=False)
    mailing_count = fields.Integer(compute="_compute_mailing_list_count", string="Number of Mailing")
    mailing_ids = fields.Many2many(
        'mailing.mailing', 'mail_mass_mailing_list_rel',
        string='Mass Mailings', copy=False)
    subscription_ids = fields.One2many(
        'mailing.contact.subscription', 'list_id',
        string='Subscription Information',
        copy=True, depends=['contact_ids'])
    is_public = fields.Boolean(
        string='Show In Preferences', default=True,
        help='The mailing list can be accessible by recipients in the subscription '
             'management page to allows them to update their preferences.')

    # ------------------------------------------------------
    # COMPUTE / ONCHANGE
    # ------------------------------------------------------

    def _compute_mailing_list_count(self):
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

    def _compute_mailing_list_statistics(self):
        """ Computes various statistics for this mailing.list that allow users
        to have a global idea of its quality (based on blacklist, opt-outs, ...).

        As some fields depend on the value of each other (mainly percentages),
        we compute everything in a single method. """

        # 1. Fetch contact data and associated counts (total / blacklist / opt-out)
        contact_statistics_per_mailing = self._fetch_contact_statistics()

        # 2. Fetch bounce data
        # Optimized SQL way of fetching the count of contacts that have
        # at least 1 message bouncing for passed mailing.lists """
        bounce_per_mailing = {}
        if self.ids:
            sql = '''
                         SELECT mclr.list_id, COUNT(DISTINCT mc.id)
                           FROM mailing_contact mc
                LEFT OUTER JOIN mailing_contact_list_rel mclr
                             ON mc.id = mclr.contact_id
                          WHERE mc.message_bounce > 0
                            AND mclr.list_id in %s
                       GROUP BY mclr.list_id
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

    def name_get(self):
        return [(list.id, "%s (%s)" % (list.name, list.contact_count)) for list in self]

    def copy(self, default=None):
        self.ensure_one()

        default = dict(default or {},
                       name=_('%s (copy)', self.name),)
        return super(MassMailingList, self).copy(default)

    # ------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------

    def action_open_import(self):
        """Open the mailing list contact import wizard."""
        action = self.env['ir.actions.actions']._for_xml_id('mass_mailing.mailing_contact_import_action')
        action['context'] = {
            **self.env.context,
            'default_mailing_list_ids': self.ids,
            'default_subscription_list_ids': [
                Command.create({'list_id': mailing_list.id})
                for mailing_list in self
            ],
        }
        return action

    def action_send_mailing(self):
        """Open the mailing form view, with the current lists set as recipients."""
        view = self.env.ref('mass_mailing.mailing_mailing_view_form_full_width')
        action = self.env["ir.actions.actions"]._for_xml_id('mass_mailing.mailing_mailing_action_mail')

        action.update({
            'context': {
                **self.env.context,
                'default_contact_list_ids': self.ids,
            },
            'target': 'current',
            'view_type': 'form',
            'views': [(view.id, 'form')],
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

    def action_mailing_lists_merge(self):
        sorted_lists = self.sorted(
            lambda list:
                (list.contact_count,
                 list.mailing_count,
                 -list.id),
            reverse=True
        )
        dest = sorted_lists[0]

        # Replace used mailing lists by the merge result
        for mailing_list in sorted_lists[1:]:
            for mailing in mailing_list.mailing_ids:
                mailing.contact_list_ids += dest
                mailing.contact_list_ids -= mailing_list

        dest.action_merge((self - dest))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Mailing Lists'),
            'res_model': 'mailing.list',
            'view_mode': 'form',
            'res_id': dest.id
        }

    def action_merge(self, src_lists):
        """
            Insert all the contact from the mailing lists 'src_lists' to the
            mailing list in 'self'. Delete mailing lists 'src_lists' after
            the merge except the destination mailing list 'self'.notes
        """
        self.ensure_one()
        # Put destination is sources lists if not already the case
        src_lists |= self
        self.env['mailing.contact'].flush_model()
        unformated_select_fields = self._mailing_list_get_select_fields()
        contact_condition = self._mailing_list_get_contact_condition()
        select_fields = [f"src_contact.{field}" for field in unformated_select_fields]
        # get every contact with contact data (email/phone)
        # that do not fully match with those of a contact in the destination list
        # and add 1 contact per tuple of distinct contact data
        # (t@t.lan, null) = (t@t.lan, null) != (t@t.lan, 0123/45.67.89)
        insert_query = f"""
            INSERT INTO mailing_contact_list_rel (contact_id, list_id)
            SELECT DISTINCT ON ({','.join(select_fields)})
                src_contact.id AS contact_id,
                %(id)s AS list_id
              FROM mailing_contact src_contact,
                  mailing_contact_list_rel src_lst_rel
             WHERE src_lst_rel.list_id IN %(ids)s
               AND src_contact.id = src_lst_rel.contact_id
               AND {contact_condition}
               -- match all contact information exactly (avoid lost data)
               -- use COALESCE to prevent postgres from equaling (NULL, X) = X
               AND ({','.join(f"COALESCE({field}, '')" for field in select_fields)}) NOT IN (
                     SELECT {','.join(f"COALESCE(sub_contact.{field}, '')" for field in unformated_select_fields)}
                       FROM mailing_contact_list_rel rel
                       JOIN mailing_contact sub_contact ON rel.contact_id=sub_contact.id
                      WHERE rel.list_id = %(id)s
               );
        """
        # for each contact data (email/phone) in the destination list
        # if one of the contacts with that data opted out in any list
        # they opt out in the destination as well
        update_query = f"""
            UPDATE mailing_contact_list_rel
               SET opt_out = TRUE
             WHERE id IN (
                    SELECT dst_lst_rel.id
                      FROM mailing_contact dst_contact,
                           mailing_contact src_contact,
                           mailing_contact_list_rel dst_lst_rel,
                           mailing_contact_list_rel src_lst_rel
                     WHERE dst_lst_rel.list_id = %(id)s
                       AND src_lst_rel.list_id IN %(ids)s
                       AND dst_contact.id = dst_lst_rel.contact_id
                       AND src_contact.id = src_lst_rel.contact_id
                       AND ({' OR '.join([f'dst_contact.{field} = src_contact.{field}' for field in unformated_select_fields])})
                       AND src_lst_rel.opt_out IS TRUE
            );
        """
        self.env.cr.execute(insert_query, ({'id': self.id, 'ids': tuple(src_lists.ids)}))
        self.env.cr.execute(update_query, ({'id': self.id, 'ids': tuple(src_lists.ids)}))
        (src_lists - self).unlink()

    def _mailing_list_get_contact_condition(self):
        return "src_contact.email_normalized NOT IN (select email from mail_blacklist where active = TRUE)"

    def _mailing_list_get_select_fields(self):
        return ["email"]

    def close_dialog(self):
        return {'type': 'ir.actions.act_window_close'}

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
                        mailing_contact_list_rel r
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
