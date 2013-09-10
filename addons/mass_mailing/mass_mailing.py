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

from datetime import date, datetime
from dateutil import relativedelta

from openerp import tools
from openerp.osv import osv, fields


class MassMailingCampaign(osv.Model):
    """Model of mass mailing campaigns.
    """
    _name = "mail.mass_mailing.campaign"
    _description = 'Mass Mailing Campaign'

    def _get_statistics(self, cr, uid, ids, name, arg, context=None):
        """ Compute statistics of the mass mailing campaign """
        results = dict.fromkeys(ids, False)
        for campaign in self.browse(cr, uid, ids, context=context):
            results[campaign.id] = {
                'sent': len(campaign.mail_ids),
                'opened': len([mail for mail in campaign.mail_ids if mail.opened]),
                'replied': len([mail for mail in campaign.mail_ids if mail.replied]),
                'bounced': len([mail for mail in campaign.mail_ids if mail.bounced]),
                # delivered: shouldn't be: all mails - (failed + bounced) ?
                'delivered': len([mail for mail in campaign.mail_ids if mail.state == 'sent' and not mail.bounced]),
            }
        return results

    def _get_segment_kanban_ids(self, cr, uid, ids, name, arg, context=None):
        results = dict.fromkeys(ids, '')
        for campaign in self.browse(cr, uid, ids, context=context):
            segment_results = []
            for segment in campaign.segment_ids:
                segment_object = {}
                for attr in ['name', 'sent', 'opened', 'replied', 'bounced']:
                    segment_object[attr] = getattr(segment, attr)
                segment_results.append(segment_object)
            results[campaign.id] = segment_results
        return results

    _columns = {
        'name': fields.char(
            'Campaign Name', required=True,
        ),
        'segment_ids': fields.one2many(
            'mail.mass_mailing.segment', 'mass_mailing_campaign_id',
            'Segments',
        ),
        'segment_kanban_ids': fields.function(
            _get_segment_kanban_ids,
            type='text', string='Segments (kanban data)',
            help='This field has for purpose to gather data about segment to display them in kanban view as nested kanban views is not possible currently',
        ),
        'mail_ids': fields.one2many(
            'mail.mail', 'mass_mailing_campaign_id',
            'Sent Emails',
        ),
        'color': fields.integer('Color Index'),
        # stat fields
        'sent': fields.function(
            _get_statistics,
            string='Sent Emails',
            type='integer', multi='_get_statistics'
        ),
        'delivered': fields.function(
            _get_statistics,
            string='Delivered',
            type='integer', multi='_get_statistics',
        ),
        'opened': fields.function(
            _get_statistics,
            string='Opened',
            type='integer', multi='_get_statistics',
        ),
        'replied': fields.function(
            _get_statistics,
            string='Replied',
            type='integer', multi='_get_statistics'
        ),
        'bounced': fields.function(
            _get_statistics,
            string='Bounced',
            type='integer', multi='_get_statistics'
        ),
    }


class MassMailingSegment(osv.Model):
    """ TODO """
    _name = 'mail.mass_mailing.segment'
    _description = 'Segment of a mass mailing campaign'
    # number of periods for tracking mail_mail statistics
    _period_number = 6

    def __get_bar_values(self, cr, uid, obj, domain, read_fields, value_field, groupby_field, context=None):
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
        # month_begin = date.today().replace(day=1)
        date_begin = date.today()
        section_result = [{'value': 0,
                           'tooltip': (date_begin + relativedelta.relativedelta(days=-i)).strftime('%d %B %Y'),
                           } for i in range(self._period_number - 1, -1, -1)]
        group_obj = obj.read_group(cr, uid, domain, read_fields, groupby_field, context=context)
        for group in group_obj:
            group_begin_date = datetime.strptime(group['__domain'][0][2], tools.DEFAULT_SERVER_DATE_FORMAT)
            month_delta = relativedelta.relativedelta(date_begin, group_begin_date)
            section_result[self._period_number - (month_delta.days + 1)] = {'value': group.get(value_field, 0), 'tooltip': group.get(groupby_field)}
        return section_result

    def _get_monthly_statistics(self, cr, uid, ids, field_name, arg, context=None):
        """ TODO
        """
        obj = self.pool.get('mail.mail')
        res = dict.fromkeys(ids, False)
        date_begin = date.today()
        context['datetime_format'] = {
            'opened': {
                'interval': 'day',
                'groupby_format': 'yyyy-mm-dd',
                'display_format': 'dd MMMM YYYY'
            },
            'replied': {
                'interval': 'day',
                'groupby_format': 'yyyy-mm-dd',
                'display_format': 'dd MMMM YYYY'
            },
        }
        groupby_begin = (date_begin + relativedelta.relativedelta(days=-4)).strftime(tools.DEFAULT_SERVER_DATE_FORMAT)
        for id in ids:
            res[id] = dict()
            domain = [('mass_mailing_segment_id', '=', id), ('opened', '>=', groupby_begin)]
            res[id]['opened_monthly'] = self.__get_bar_values(cr, uid, obj, domain, ['opened'], 'opened_count', 'opened', context=context)
            domain = [('mass_mailing_segment_id', '=', id), ('replied', '>=', groupby_begin)]
            res[id]['replied_monthly'] = self.__get_bar_values(cr, uid, obj, domain, ['replied'], 'replied_count', 'replied', context=context)
        return res

    def _get_statistics(self, cr, uid, ids, name, arg, context=None):
        """ Compute statistics of the mass mailing campaign """
        results = dict.fromkeys(ids, False)
        for segment in self.browse(cr, uid, ids, context=context):
            results[segment.id] = {
                'sent': len(segment.mail_ids),
                'delivered': len([mail for mail in segment.mail_ids if mail.state == 'sent' and not mail.bounced]),
                'opened': len([mail for mail in segment.mail_ids if mail.opened]),
                'replied': len([mail for mail in segment.mail_ids if mail.replied]),
                'bounced': len([mail for mail in segment.mail_ids if mail.bounced]),
            }
        return results

    _columns = {
        'name': fields.char('Name', required=True),
        'mass_mailing_campaign_id': fields.many2one(
            'mail.mass_mailing.campaign', 'Mass Mailing Campaign',
            ondelete='cascade',
        ),
        'template_id': fields.many2one(
            'email.template', 'Email Template',
            ondelete='set null',
        ),
        'domain': fields.char('Domain'),
        'date': fields.datetime('Date'),
        # mail_mail data
        'mail_ids': fields.one2many(
            'mail.mail', 'mass_mailing_segment_id',
            'Send Emails',
        ),
        'sent': fields.function(
            _get_statistics,
            string='Sent Emails',
            type='integer', multi='_get_statistics'
        ),
        'delivered': fields.function(
            _get_statistics,
            string='Delivered',
            type='integer', multi='_get_statistics',
        ),
        'opened': fields.function(
            _get_statistics,
            string='Opened',
            type='integer', multi='_get_statistics',
        ),
        'replied': fields.function(
            _get_statistics,
            string='Replied',
            type='integer', multi='_get_statistics'
        ),
        'bounced': fields.function(
            _get_statistics,
            string='Bounce',
            type='integer', multi='_get_statistics'
        ),
        # monthly ratio
        'opened_monthly': fields.function(
            _get_monthly_statistics,
            string='Sent Emails',
            type='char', multi='_get_monthly_statistics',
        ),
        'replied_monthly': fields.function(
            _get_monthly_statistics,
            string='Replied',
            type='char', multi='_get_monthly_statistics',
        ),
    }
