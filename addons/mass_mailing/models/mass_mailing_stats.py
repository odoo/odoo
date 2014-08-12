# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

import openerp
from openerp.osv import fields, osv
from openerp import models, api, _


class MailMailStats(osv.Model):
    """ MailMailStats models the statistics collected about emails. Those statistics
    are stored in a separated model and table to avoid bloating the mail_mail table
    with statistics values. This also allows to delete emails send with mass mailing
    without loosing the statistics about them. """

    _name = 'mail.mail.statistics'
    _description = 'Email Statistics'
    _rec_name = 'message_id'
    _order = 'message_id'

    def get_first_click(self, cr, uid, ids, name, args, context=None):
        click_obj = self.pool.get('website.alias.click')
        res = {}
        for alias in self.browse(cr, uid, ids, context=context):
            max_id = max([al.id for al in alias.alias_click_ids if al])
            alias_click = self.pool.get('website.alias.click').browse(cr, uid, max_id, context=context)
            res[alias.id] = alias_click.click_date
        return res

    def click_alias(self, cr, uid, ids, context=None):
        for click in self.browse(cr, uid, ids, context=context):
            return self.pool.get('mail.mail.statistics').search(cr, uid, [('id', '=', click.mail_stat_id.id)], context=context)
        return []

    _columns = {
        'mail_mail_id': fields.many2one('mail.mail', 'Mail ID', ondelete='set null'),
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
        'alias_click_ids': fields.one2many('website.alias.click','mail_stat_id', 'Alias click'),
        'first_click': fields.function(get_first_click,'First Click', type='date',
                    store = {'mail.mail.statistics': (lambda self, cr, uid, ids, ctx: ids, ['alias_click_ids'], 10),
                             'website.alias.click': (click_alias, ['mail_stat_id'], 10)}),
    }

    _defaults = {
        'scheduled': fields.datetime.now,
    }

    def _get_ids(self, cr, uid, ids=None, mail_mail_ids=None, mail_message_ids=None, domain=None, context=None):
        if not ids and mail_mail_ids:
            base_domain = [('mail_mail_id', 'in', mail_mail_ids)]
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

class website_alias_click(models.Model):
    _inherit = "website.alias.click"

    mail_stat_id = openerp.fields.Many2one('mail.mail.statistics', string='Mail Statistics',
            help="It will link the statistics with the click data")

