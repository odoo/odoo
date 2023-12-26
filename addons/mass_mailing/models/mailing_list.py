# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import UserError


class MassMailingList(models.Model):
    """Model of a contact list. """
    _name = 'mailing.list'
    _order = 'name'
    _description = 'Mailing List'

    name = fields.Char(string='Mailing List', required=True)
    active = fields.Boolean(default=True)
    contact_nbr = fields.Integer(compute="_compute_contact_nbr", string='Number of Contacts')
    contact_ids = fields.Many2many(
        'mailing.contact', 'mailing_contact_list_rel', 'list_id', 'contact_id',
        string='Mailing Lists')
    subscription_ids = fields.One2many(
        'mailing.contact.subscription', 'list_id', string='Subscription Information',
        depends=['contact_ids'])
    is_public = fields.Boolean(default=True, help="The mailing list can be accessible by recipient in the unsubscription"
                                                  " page to allows him to update his subscription preferences.")

    # Compute number of contacts non opt-out, non blacklisted and valid email recipient for a mailing list
    def _compute_contact_nbr(self):
        if self.ids:
            self.env.cr.execute('''
                select
                    list_id, count(*)
                from
                    mailing_contact_list_rel r
                    left join mailing_contact c on (r.contact_id=c.id)
                    left join mail_blacklist bl on c.email_normalized = bl.email and bl.active
                where
                    list_id in %s
                    AND COALESCE(r.opt_out,FALSE) = FALSE
                    AND c.email_normalized IS NOT NULL
                    AND bl.id IS NULL
                group by
                    list_id
            ''', (tuple(self.ids), ))
            data = dict(self.env.cr.fetchall())
            for mailing_list in self:
                mailing_list.contact_nbr = data.get(mailing_list._origin.id, 0)
        else:
            self.contact_nbr = 0

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
        return [(list.id, "%s (%s)" % (list.name, list.contact_nbr)) for list in self]

    def action_view_contacts(self):
        action = self.env["ir.actions.actions"]._for_xml_id("mass_mailing.action_view_mass_mailing_contacts")
        action['domain'] = [('list_ids', 'in', self.ids)]
        context = dict(self.env.context, search_default_filter_valid_email_recipient=1, default_list_ids=self.ids)
        action['context'] = context
        return action

    def action_merge(self, src_lists, archive):
        """
            Insert all the contact from the mailing lists 'src_lists' to the
            mailing list in 'self'. Possibility to archive the mailing lists
            'src_lists' after the merge except the destination mailing list 'self'.
        """
        # Explation of the SQL query with an example. There are the following lists
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
        # The row_column is kind of an occurence counter for the email address.
        # Then we create the Many2many relation between the destination list and the contacts
        # while avoiding to insert an existing email address (if the destination is in the source
        # for example)
        self.ensure_one()
        # Put destination is sources lists if not already the case
        src_lists |= self
        self.env['mailing.contact'].flush(['email', 'email_normalized'])
        self.env['mailing.contact.subscription'].flush(['contact_id', 'opt_out', 'list_id'])
        self.env.cr.execute("""
            INSERT INTO mailing_contact_list_rel (contact_id, list_id)
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
                    mailing_contact_list_rel contact_list_rel,
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
                        mailing_contact_list_rel contact_list_rel2
                    WHERE contact2.email = contact.email
                    AND contact_list_rel2.contact_id = contact2.id
                    AND contact_list_rel2.list_id = %s
                    )
                ) st
            WHERE st.rn = 1;""", (self.id, tuple(src_lists.ids), self.id))
        self.flush()
        self.invalidate_cache()
        if archive:
            (src_lists - self).action_archive()

    def close_dialog(self):
        return {'type': 'ir.actions.act_window_close'}
