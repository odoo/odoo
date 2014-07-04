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

from openerp import tools
from openerp.tools.translate import _
from openerp.osv import osv, fields


class MassMailingCampaign(osv.Model):
    """Model of mass mailing campaigns.
    """
    _name = "mail.mass_mailing.campaign"
    _description = 'Mass Mailing Campaign'
    # number of embedded mailings in kanban view
    _kanban_mailing_nbr = 4

    def _get_statistics(self, cr, uid, ids, name, arg, context=None):
        """ Compute statistics of the mass mailing campaign """
        results = {}
        cr.execute("""
            SELECT
                c.id,
                COUNT(s.id) AS sent,
                COUNT(CASE WHEN s.id is not null AND s.bounced is null THEN 1 ELSE null END) AS delivered,
                COUNT(CASE WHEN s.opened is not null THEN 1 ELSE null END) AS opened,
                COUNT(CASE WHEN s.replied is not null THEN 1 ELSE null END) AS replied ,
                COUNT(CASE WHEN s.bounced is not null THEN 1 ELSE null END) AS bounced
            FROM
                mail_mail_statistics s
            RIGHT JOIN
                mail_mass_mailing_campaign c
                ON (c.id = s.mass_mailing_campaign_id)
            WHERE
                c.id IN %s
            GROUP BY
                c.id
        """, (tuple(ids), ))
        for (campaign_id, sent, delivered, opened, replied, bounced) in cr.fetchall():
            results[campaign_id] = {
                'sent': sent,
                # delivered: shouldn't be: all mails - (failed + bounced) ?
                'delivered': delivered,
                'opened': opened,
                'replied': replied,
                'bounced': bounced,
            }
        return results

    def _get_mass_mailing_kanban_ids(self, cr, uid, ids, name, arg, context=None):
        """ Gather data about mass mailings to display them in kanban view as
        nested kanban views is not possible currently. """
        results = dict.fromkeys(ids, '')
        for campaign_id in ids:
            mass_mailing_results = []
            mass_mailing_results = self.pool['mail.mass_mailing'].search_read(cr, uid,
                            domain=[('mass_mailing_campaign_id', '=', campaign_id)],
                            fields=['name', 'sent', 'delivered', 'opened', 'replied', 'bounced'],
                            limit=self._kanban_mailing_nbr,
                            context=context)
            results[campaign_id] = mass_mailing_results
        return results

    _columns = {
        'name': fields.char(
            'Campaign Name', required=True,
        ),
        'user_id': fields.many2one(
            'res.users', 'Responsible',
            required=True,
        ),
        'mass_mailing_ids': fields.one2many(
            'mail.mass_mailing', 'mass_mailing_campaign_id',
            'Mass Mailings',
        ),
        'mass_mailing_kanban_ids': fields.function(
            _get_mass_mailing_kanban_ids,
            type='text', string='Mass Mailings (kanban data)',
            help='This field has for purpose to gather data about mass mailings '
                 'to display them in kanban view as nested kanban views is not '
                 'possible currently',
        ),
        'statistics_ids': fields.one2many(
            'mail.mail.statistics', 'mass_mailing_campaign_id',
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

    _defaults = {
        'user_id': lambda self, cr, uid, ctx=None: uid,
    }

    def launch_mass_mailing_create_wizard(self, cr, uid, ids, context=None):
        ctx = dict(context)
        ctx.update({
            'default_mass_mailing_campaign_id': ids[0],
        })
        return {
            'name': _('Create a Mass Mailing for the Campaign'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.mass_mailing.create',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }


class MassMailing(osv.Model):
    """ MassMailing models a wave of emails for a mass mailign campaign.
    A mass mailing is an occurence of sending emails. """

    _name = 'mail.mass_mailing'
    _description = 'Wave of sending emails'
    # number of periods for tracking mail_mail statistics
    _period_number = 6
    _order = 'date DESC'

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
            res[id]['opened_monthly'] = self.__get_bar_values(cr, uid, id, obj, domain, ['opened'], 'opened_count', 'opened:day', context=context)
            domain = [('mass_mailing_id', '=', id), ('replied', '>=', date_begin_str), ('replied', '<=', date_end_str)]
            res[id]['replied_monthly'] = self.__get_bar_values(cr, uid, id, obj, domain, ['replied'], 'replied_count', 'replied:day', context=context)
        return res

    def _get_statistics(self, cr, uid, ids, name, arg, context=None):
        """ Compute statistics of the mass mailing """
        results = {}
        cr.execute("""
            SELECT
                m.id,
                COUNT(s.id) AS sent,
                COUNT(CASE WHEN s.id is not null AND s.bounced is null THEN 1 ELSE null END) AS delivered,
                COUNT(CASE WHEN s.opened is not null THEN 1 ELSE null END) AS opened,
                COUNT(CASE WHEN s.replied is not null THEN 1 ELSE null END) AS replied ,
                COUNT(CASE WHEN s.bounced is not null THEN 1 ELSE null END) AS bounced
            FROM
                mail_mail_statistics s
            RIGHT JOIN
                mail_mass_mailing m
                ON (m.id = s.mass_mailing_id)
            WHERE
                m.id IN %s
            GROUP BY
                m.id
        """, (tuple(ids), ))
        for (mass_mailing_id, sent, delivered, opened, replied, bounced) in cr.fetchall():
            results[mass_mailing_id] = {
                'sent': sent,
                # delivered: shouldn't be: all mails - (failed + bounced) ?
                'delivered': delivered,
                'opened': opened,
                'replied': replied,
                'bounced': bounced,
            }
        return results

    _columns = {
        'name': fields.char('Name', required=True),
        'mass_mailing_campaign_id': fields.many2one(
            'mail.mass_mailing.campaign', 'Mass Mailing Campaign',
            ondelete='cascade', required=True,
        ),
        'template_id': fields.many2one(
            'email.template', 'Email Template',
            ondelete='set null',
        ),
        'domain': fields.char('Domain'),
        'date': fields.datetime('Date'),
        'color': fields.related(
            'mass_mailing_campaign_id', 'color',
            type='integer', string='Color Index',
        ),
        # statistics data
        'statistics_ids': fields.one2many(
            'mail.mail.statistics', 'mass_mailing_id',
            'Emails Statistics',
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
            _get_daily_statistics,
            string='Opened',
            type='char', multi='_get_daily_statistics',
        ),
        'replied_monthly': fields.function(
            _get_daily_statistics,
            string='Replied',
            type='char', multi='_get_daily_statistics',
        ),
    }

    _defaults = {
        'date': fields.datetime.now,
    }


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
        'message_id': fields.char(
            'Message-ID',
        ),
        'model': fields.char(
            'Document model',
        ),
        'res_id': fields.integer(
            'Document ID',
        ),
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
        'template_id': fields.related(
            'mass_mailing_id', 'template_id',
            type='many2one', ondelete='set null',
            relation='email.template',
            string='Email Template',
            store=True, readonly=True,
        ),
        # Bounce and tracking
        'opened': fields.datetime(
            'Opened',
            help='Date when this email has been opened for the first time.'),
        'replied': fields.datetime(
            'Replied',
            help='Date when this email has been replied for the first time.'),
        'bounced': fields.datetime(
            'Bounced',
            help='Date when this email has bounced.'
        ),
    }

    def set_opened(self, cr, uid, ids=None, mail_mail_ids=None, mail_message_ids=None, context=None):
        """ Set as opened """
        if not ids and mail_mail_ids:
            ids = self.search(cr, uid, [('mail_mail_id', 'in', mail_mail_ids)], context=context)
        elif not ids and mail_message_ids:
            ids = self.search(cr, uid, [('message_id', 'in', mail_message_ids)], context=context)
        else:
            ids = []
        for stat in self.browse(cr, uid, ids, context=context):
            if not stat.opened:
                self.write(cr, uid, [stat.id], {'opened': fields.datetime.now()}, context=context)
        return ids

    def set_replied(self, cr, uid, ids=None, mail_mail_ids=None, mail_message_ids=None, context=None):
        """ Set as replied """
        if not ids and mail_mail_ids:
            ids = self.search(cr, uid, [('mail_mail_id', 'in', mail_mail_ids)], context=context)
        elif not ids and mail_message_ids:
            ids = self.search(cr, uid, [('message_id', 'in', mail_message_ids)], context=context)
        else:
            ids = []
        for stat in self.browse(cr, uid, ids, context=context):
            if not stat.replied:
                self.write(cr, uid, [stat.id], {'replied': fields.datetime.now()}, context=context)
        return ids

    def set_bounced(self, cr, uid, ids=None, mail_mail_ids=None, mail_message_ids=None, context=None):
        """ Set as bounced """
        if not ids and mail_mail_ids:
            ids = self.search(cr, uid, [('mail_mail_id', 'in', mail_mail_ids)], context=context)
        elif not ids and mail_message_ids:
            ids = self.search(cr, uid, [('message_id', 'in', mail_message_ids)], context=context)
        else:
            ids = []
        for stat in self.browse(cr, uid, ids, context=context):
            if not stat.bounced:
                self.write(cr, uid, [stat.id], {'bounced': fields.datetime.now()}, context=context)
        return ids
