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

from datetime import datetime
from dateutil import relativedelta
import random
try:
    import simplejson as json
except ImportError:
    import json
import urllib
import urlparse

from openerp import tools
from openerp.exceptions import Warning
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools.translate import _
from openerp.osv import osv, fields

class MassMailingList(osv.Model):
    _inherit = 'mail.mass_mailing.list'
    def _get_contact_nbr(self, cr, uid, ids, name, arg, context=None):
        result = dict.fromkeys(ids, 0)
        mlc = self.pool.get('mail.mass_mailing.contact')
        for m in mlc.read_group(cr, uid, [('list_id','in',ids)], ['list_id'], ['list_id'], context=context):
            result[m['list_id'][0]] = m['list_id_count']
        return result

    _columns = {
        'contact_nbr': fields.function(
            _get_contact_nbr, type='integer',
            string='Number of Contacts',
        ),
    }


class MassMailingCampaign(osv.Model):
    _inherit = "mail.mass_mailing.campaign"
    def _get_statistics(self, cr, uid, ids, name, arg, context=None):
        """ Compute statistics of the mass mailing campaign """
        Statistics = self.pool['mail.mail.statistics']
        results = dict.fromkeys(ids, False)
        for cid in ids:
            stat_ids = Statistics.search(cr, uid, [('mass_mailing_campaign_id', '=', cid)], context=context)
            stats = Statistics.browse(cr, uid, stat_ids, context=context)
            results[cid] = {
                'total': len(stats),
                'failed': len([s for s in stats if not s.scheduled is False and s.sent is False and not s.exception is False]),
                'scheduled': len([s for s in stats if not s.scheduled is False and s.sent is False and s.exception is False]),
                'sent': len([s for s in stats if not s.sent is False]),
                'opened': len([s for s in stats if not s.opened is False]),
                'replied': len([s for s in stats if not s.replied is False]),
                'bounced': len([s for s in stats if not s.bounced is False]),
            }
            results[cid]['delivered'] = results[cid]['sent'] - results[cid]['bounced']
            results[cid]['received_ratio'] = 100.0 * results[cid]['delivered'] / (results[cid]['sent'] or 1)
            results[cid]['opened_ratio'] = 100.0 * results[cid]['opened'] / (results[cid]['sent'] or 1)
            results[cid]['replied_ratio'] = 100.0 * results[cid]['replied'] / (results[cid]['sent'] or 1)
        return results

    _columns = {
        'total': fields.function(
            _get_statistics, string='Total',
            type='integer', multi='_get_statistics'
        ),
        'scheduled': fields.function(
            _get_statistics, string='Scheduled',
            type='integer', multi='_get_statistics'
        ),
        'failed': fields.function(
            _get_statistics, string='Failed',
            type='integer', multi='_get_statistics'
        ),
        'sent': fields.function(
            _get_statistics, string='Sent Emails',
            type='integer', multi='_get_statistics'
        ),
        'delivered': fields.function(
            _get_statistics, string='Delivered',
            type='integer', multi='_get_statistics',
        ),
        'opened': fields.function(
            _get_statistics, string='Opened',
            type='integer', multi='_get_statistics',
        ),
        'replied': fields.function(
            _get_statistics, string='Replied',
            type='integer', multi='_get_statistics'
        ),
        'bounced': fields.function(
            _get_statistics, string='Bounced',
            type='integer', multi='_get_statistics'
        ),
        'received_ratio': fields.function(
            _get_statistics, string='Received Ratio',
            type='integer', multi='_get_statistics',
        ),
        'opened_ratio': fields.function(
            _get_statistics, string='Opened Ratio',
            type='integer', multi='_get_statistics',
        ),
        'replied_ratio': fields.function(
            _get_statistics, string='Replied Ratio',
            type='integer', multi='_get_statistics',
        ),
    }


class MassMailing(osv.Model):
    _inherit = 'mail.mass_mailing'
    _period_number = 6
    def __get_bar_values(self, cr, uid, id, obj, domain, read_fields, value_field, groupby_field, context=None):
        """ Generic method to generate data for bar chart values using SparklineBarWidget.
            This method performs obj.read_group(cr, uid, domain, read_fields, groupby_field).

            :param obj: the target model (i.e. crm_lead)
            :param domain: the domain applied to the read_group
            :param list read_fields: the list of fields to read in the read_group
            :param str value_field: the field used to compute the value of the bar slice
            :param str groupby_field: the fields used to group

            :return list section_result: a list of dicts: [
                                                {   'value': (int) bar_column_value,
                                                    'tootip': (str) bar_column_tooltip,
                                                }
                                            ]
        """
        date_begin = datetime.strptime(self.browse(cr, uid, id, context=context).date, tools.DEFAULT_SERVER_DATETIME_FORMAT).date()
        section_result = [{'value': 0,
                           'tooltip': (date_begin + relativedelta.relativedelta(days=i)).strftime('%d %B %Y'),
                           } for i in range(0, self._period_number)]
        group_obj = obj.read_group(cr, uid, domain, read_fields, groupby_field, context=context)
        field_col_info = obj._all_columns.get(groupby_field.split(':')[0])
        pattern = tools.DEFAULT_SERVER_DATE_FORMAT if field_col_info.column._type == 'date' else tools.DEFAULT_SERVER_DATETIME_FORMAT
        for group in group_obj:
            group_begin_date = datetime.strptime(group['__domain'][0][2], pattern).date()
            timedelta = relativedelta.relativedelta(group_begin_date, date_begin)
            section_result[timedelta.days] = {'value': group.get(value_field, 0), 'tooltip': group.get(groupby_field)}
        return section_result

    def _get_daily_statistics(self, cr, uid, ids, field_name, arg, context=None):
        """ Get the daily statistics of the mass mailing. This is done by a grouping
        on opened and replied fields. Using custom format in context, we obtain
        results for the next 6 days following the mass mailing date. """
        obj = self.pool['mail.mail.statistics']
        res = {}
        for id in ids:
            res[id] = {}
            date_begin = datetime.strptime(self.browse(cr, uid, id, context=context).date, tools.DEFAULT_SERVER_DATETIME_FORMAT)
            date_end = date_begin + relativedelta.relativedelta(days=self._period_number - 1)
            date_begin_str = date_begin.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
            date_end_str = date_end.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
            domain = [('mass_mailing_id', '=', id), ('opened', '>=', date_begin_str), ('opened', '<=', date_end_str)]
            res[id]['opened_dayly'] = json.dumps(self.__get_bar_values(cr, uid, id, obj, domain, ['opened'], 'opened_count', 'opened:day', context=context))
            domain = [('mass_mailing_id', '=', id), ('replied', '>=', date_begin_str), ('replied', '<=', date_end_str)]
            res[id]['replied_dayly'] = json.dumps(self.__get_bar_values(cr, uid, id, obj, domain, ['replied'], 'replied_count', 'replied:day', context=context))
        return res

    def _get_statistics(self, cr, uid, ids, name, arg, context=None):
        """ Compute statistics of the mass mailing campaign """
        Statistics = self.pool['mail.mail.statistics']
        results = dict.fromkeys(ids, False)
        for mid in ids:
            stat_ids = Statistics.search(cr, uid, [('mass_mailing_id', '=', mid)], context=context)
            stats = Statistics.browse(cr, uid, stat_ids, context=context)
            results[mid] = {
                'total': len(stats),
                'failed': len([s for s in stats if not s.scheduled is False and s.sent is False and not s.exception is False]),
                'scheduled': len([s for s in stats if not s.scheduled is False and s.sent is False and s.exception is False]),
                'sent': len([s for s in stats if not s.sent is False]),
                'opened': len([s for s in stats if not s.opened is False]),
                'replied': len([s for s in stats if not s.replied is False]),
                'bounced': len([s for s in stats if not s.bounced is False]),
            }
            results[mid]['delivered'] = results[mid]['sent'] - results[mid]['bounced']
            results[mid]['received_ratio'] = 100.0 * results[mid]['delivered'] / (results[mid]['sent'] or 1)
            results[mid]['opened_ratio'] = 100.0 * results[mid]['opened'] / (results[mid]['sent'] or 1)
            results[mid]['replied_ratio'] = 100.0 * results[mid]['replied'] / (results[mid]['sent'] or 1)
        return results

    # To improve
    def _get_contact_nbr(self, cr, uid, ids, name, arg, context=None):
        res = dict.fromkeys(ids, False)
        for mailing in self.browse(cr, uid, ids, context=context):
            if not mailing.mailing_domain:
                res[mailing.id] = 0
                continue
            res[mailing.id] = self.pool[mailing.mailing_model].search(
                cr, uid, eval(mailing.mailing_domain), count=True, context=context
            )
        return res

    _columns = {
        'contact_nbr': fields.function(_get_contact_nbr, type='integer', string='Contact Number'),
        # statistics data
        'statistics_ids': fields.one2many(
            'mail.mail.statistics', 'mass_mailing_id',
            'Emails Statistics',
        ),
        'total': fields.function(
            _get_statistics, string='Total',
            type='integer', multi='_get_statistics',
        ),
        'scheduled': fields.function(
            _get_statistics, string='Scheduled',
            type='integer', multi='_get_statistics',
        ),
        'failed': fields.function(
            _get_statistics, string='Failed',
            type='integer', multi='_get_statistics',
        ),
        'sent': fields.function(
            _get_statistics, string='Sent',
            type='integer', multi='_get_statistics',
        ),
        'delivered': fields.function(
            _get_statistics, string='Delivered',
            type='integer', multi='_get_statistics',
        ),
        'opened': fields.function(
            _get_statistics, string='Opened',
            type='integer', multi='_get_statistics',
        ),
        'replied': fields.function(
            _get_statistics, string='Replied',
            type='integer', multi='_get_statistics',
        ),
        'bounced': fields.function(
            _get_statistics, string='Bounced',
            type='integer', multi='_get_statistics',
        ),
        'received_ratio': fields.function(
            _get_statistics, string='Received Ratio',
            type='integer', multi='_get_statistics',
        ),
        'opened_ratio': fields.function(
            _get_statistics, string='Opened Ratio',
            type='integer', multi='_get_statistics',
        ),
        'replied_ratio': fields.function(
            _get_statistics, string='Replied Ratio',
            type='integer', multi='_get_statistics',
        ),
        # dayly ratio
        'opened_dayly': fields.function(
            _get_daily_statistics, string='Opened',
            type='char', multi='_get_daily_statistics',
            oldname='opened_monthly',
        ),
        'replied_dayly': fields.function(
            _get_daily_statistics, string='Replied',
            type='char', multi='_get_daily_statistics',
            oldname='replied_monthly',
        ),
    }




# Merge this on emails
class MailMailStats(osv.Model):
    """ MailMailStats models the statistics collected about emails. Those statistics
    are stored in a separated model and table to avoid bloating the mail_mail table
    with statistics values. This also allows to delete emails send with mass mailing
    without loosing the statistics about them. """

    _name = 'mail.mail.statistics'
    _description = 'Email Statistics'
    _rec_name = 'message_id'
    _order = 'message_id'

    _columns = {
        'mail_mail_id': fields.integer(
            'Mail ID',
            help='ID of the related mail_mail. This field is an integer field because'
                 'the related mail_mail can be deleted separately from its statistics.'
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

