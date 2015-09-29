# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class MailMailStats(osv.Model):
    """ MailMailStats models the statistics collected about emails. Those statistics
    are stored in a separated model and table to avoid bloating the mail_mail table
    with statistics values. This also allows to delete emails send with mass mailing
    without loosing the statistics about them. """

    _name = 'mail.mail.statistics'
    _description = 'Email Statistics'
    _rec_name = 'message_id'
    _order = 'message_id'

    def _compute_state(self, cr, uid, ids, field_names, arg, context=None):
        res = dict((i, {'state': 'outgoing', 'state_update': fields.datetime.now()}) for i in ids)

        for stat in self.browse(cr, uid, ids, context=context):
            if stat.exception:
                res[stat.id]['state'] = 'exception'
            if stat.sent:
                res[stat.id]['state'] = 'sent'
            if stat.opened:
                res[stat.id]['state'] = 'opened'
            if stat.replied:
                res[stat.id]['state'] = 'replied'
            if stat.bounced:
                res[stat.id]['state'] = 'bounced'

        return res

    def _compute_recipient(self, cr, uid, ids, field_names, arg, context=None):
        res = dict.fromkeys(ids, '')
        for stat in self.browse(cr, uid, ids, context=context):
            if not self.pool.get(stat.model):
                continue
            target = self.pool[stat.model].browse(cr, uid, stat.res_id, context=context)
            email = ''
            for email_field in ('email', 'email_from'):
                if email_field in target and target[email_field]:
                    email = ' <%s>' % target[email_field]
                    break
            res[stat.id] = '%s%s' % (target.display_name, email)
        return res

    __store = {_name: ((lambda s, c, u, i, t: i), ['exception', 'sent', 'opened', 'replied', 'bounced'], 10)}

    _columns = {
        'mail_mail_id': fields.many2one('mail.mail', 'Mail', ondelete='set null', select=True),
        'mail_mail_id_int': fields.integer(
            'Mail ID (tech)',
            help='ID of the related mail_mail. This field is an integer field because'
                 'the related mail_mail can be deleted separately from its statistics.'
                 'However the ID is needed for several action and controllers.'
        ),
        'message_id': fields.char('Message-ID'),
        'model': fields.char('Document model'),
        'res_id': fields.integer('Document ID'),
        # campaign / wave data
        'mass_mailing_id': fields.many2one(
            'mail.mass_mailing', 'Mass Mailing',
            ondelete='set null',
        ),
        'mass_mailing_campaign_id': fields.related(
            'mass_mailing_id', 'mass_mailing_campaign_id',
            type='many2one', ondelete='set null',
            relation='mail.mass_mailing.campaign',
            string='Mass Mailing Campaign',
            store=True, readonly=True,
        ),
        # Bounce and tracking
        'scheduled': fields.datetime('Scheduled', help='Date when the email has been created'),
        'sent': fields.datetime('Sent', help='Date when the email has been sent'),
        'exception': fields.datetime('Exception', help='Date of technical error leading to the email not being sent'),
        'opened': fields.datetime('Opened', help='Date when the email has been opened the first time'),
        'replied': fields.datetime('Replied', help='Date when this email has been replied for the first time.'),
        'bounced': fields.datetime('Bounced', help='Date when this email has bounced.'),
        'links_click_ids': fields.one2many('link.tracker.click', 'mail_stat_id', 'Links click'),
        'state': fields.function(_compute_state, string='State', type="selection", multi="state",
                                 selection=[('outgoing', 'Outgoing'),
                                            ('exception', 'Exception'),
                                            ('sent', 'Sent'),
                                            ('opened', 'Opened'),
                                            ('replied', 'Replied'),
                                            ('bounced', 'Bounced')],
                                 store=__store),
        'state_update': fields.function(_compute_state, string='State Update', type='datetime',
                                        multi='state', help='Last state update of the mail',
                                        store=__store),
        'recipient': fields.function(_compute_recipient, string='Recipient', type='char'),
    }

    _defaults = {
        'scheduled': fields.datetime.now,
    }

    def create(self, cr, uid, values, context=None):
        if 'mail_mail_id' in values:
            values['mail_mail_id_int'] = values['mail_mail_id']
        res = super(MailMailStats, self).create(cr, uid, values, context=context)
        return res

    def _get_ids(self, cr, uid, ids=None, mail_mail_ids=None, mail_message_ids=None, domain=None, context=None):
        if not ids and mail_mail_ids:
            base_domain = [('mail_mail_id_int', 'in', mail_mail_ids)]
        elif not ids and mail_message_ids:
            base_domain = [('message_id', 'in', mail_message_ids)]
        else:
            base_domain = [('id', 'in', ids or [])]
        if domain:
            base_domain = ['&'] + domain + base_domain
        return self.search(cr, uid, base_domain, context=context)

    def set_opened(self, cr, uid, ids=None, mail_mail_ids=None, mail_message_ids=None, context=None):
        stat_ids = self._get_ids(cr, uid, ids, mail_mail_ids, mail_message_ids, [('opened', '=', False)], context)
        self.write(cr, uid, stat_ids, {'opened': fields.datetime.now()}, context=context)
        return stat_ids

    def set_replied(self, cr, uid, ids=None, mail_mail_ids=None, mail_message_ids=None, context=None):
        stat_ids = self._get_ids(cr, uid, ids, mail_mail_ids, mail_message_ids, [('replied', '=', False)], context)
        self.write(cr, uid, stat_ids, {'replied': fields.datetime.now()}, context=context)
        return stat_ids

    def set_bounced(self, cr, uid, ids=None, mail_mail_ids=None, mail_message_ids=None, context=None):
        stat_ids = self._get_ids(cr, uid, ids, mail_mail_ids, mail_message_ids, [('bounced', '=', False)], context)
        self.write(cr, uid, stat_ids, {'bounced': fields.datetime.now()}, context=context)
        return stat_ids
