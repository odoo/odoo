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


class MassMailingCategory(osv.Model):
    """Model of categories of mass mailing, i.e. marketing, newsletter, ... """
    _name = 'mail.mass_mailing.category'
    _description = 'Mass Mailing Category'

    _columns = {
        'name': fields.char('Name', required=True),
    }


class MassMailingContact(osv.Model):
    """Model of a contact. This model is different from the partner model
    because it holds only some basic information: name, email. The purpose is to
    be able to deal with large contact list to email without bloating the partner
    database. """
    _name = 'mail.mass_mailing.contact'
    _description = 'Mass Mailing Contact'

    _columns = {
        'name': fields.char('Name', required=True),
        'email': fields.char('Email', required=True),
        'list_id': fields.many2one(
            'mail.mass_mailing.list', string='Mailing List',
            domain=[('model', '=', 'mail.mass_mailing.contact')],
            ondelete='cascade',
        ),
        'opt_out': fields.boolean('Opt Out', help='The contact has chosen not to receive news anymore from this mailing list'),
    }

    def name_create(self, cr, uid, name, context=None):
        name, email = self.pool['res.partner']._parse_partner_name(name, context=context)
        if name and not email:
            email = name
        if email and not name:
            name = email
        rec_id = self.create(cr, uid, {'name': name, 'email': email}, context=context)
        return self.name_get(cr, uid, [rec_id], context)[0]


class MassMailingList(osv.Model):
    """Model of a contact list. """
    _name = 'mail.mass_mailing.list'
    _description = 'Contact List'

    def default_get(self, cr, uid, fields, context=None):
        """Override default_get to handle active_domain coming from the list view. """
        res = super(MassMailingList, self).default_get(cr, uid, fields, context=context)
        if 'domain' in fields:
            if not 'model' in res and context.get('active_model'):
                res['model'] = context['active_model']
            if 'active_domain' in context:
                res['domain'] = '%s' % context['active_domain']
            elif 'active_ids' in context:
                res['domain'] = '%s' % [('id', 'in', context['active_ids'])]
            else:
                res['domain'] = False
        return res

    def _get_contact_nbr(self, cr, uid, ids, name, arg, context=None):
        """Compute the number of contacts linked to the mailing list. """
        results = dict.fromkeys(ids, 0)
        for contact_list in self.browse(cr, uid, ids, context=context):
            results[contact_list.id] = self.pool[contact_list.model].search(
                cr, uid,
                self._get_domain(cr, uid, [contact_list.id], context=context)[contact_list.id],
                count=True, context=context
            )
        return results

    def _get_model_list(self, cr, uid, context=None):
        return self.pool['mail.mass_mailing']._get_mailing_model(cr, uid, context=context)

    # indirections for inheritance
    _model_list = lambda self, *args, **kwargs: self._get_model_list(*args, **kwargs)

    _columns = {
        'name': fields.char('Name', required=True),
        'contact_nbr': fields.function(
            _get_contact_nbr, type='integer',
            string='Contact Number',
        ),
        'model': fields.selection(
            _model_list, type='char', required=True,
            string='Applies To'
        ),
        'filter_id': fields.many2one(
            'ir.filters', string='Custom Filter',
            domain="[('model_id.model', '=', model)]",
        ),
        'domain': fields.text('Domain'),
    }

    def on_change_model(self, cr, uid, ids, model, context=None):
        return {'value': {'filter_id': False}}

    def on_change_filter_id(self, cr, uid, ids, filter_id, context=None):
        values = {}
        if filter_id:
            ir_filter = self.pool['ir.filters'].browse(cr, uid, filter_id, context=context)
            values['domain'] = ir_filter.domain
        return {'value': values}

    def on_change_domain(self, cr, uid, ids, domain, model, context=None):
        if domain is False:
            return {'value': {'contact_nbr': 0}}
        else:
            domain = eval(domain)
            return {'value': {'contact_nbr': self.pool[model].search(cr, uid, domain, context=context, count=True)}}

    def create(self, cr, uid, values, context=None):
        new_id = super(MassMailingList, self).create(cr, uid, values, context=context)
        if values.get('model') == 'mail.mass_mailing.contact' and (not context or not context.get('no_contact_to_list')):
            domain = values.get('domain')
            if domain is None or domain is False:
                return new_id
            contact_ids = self.pool['mail.mass_mailing.contact'].search(cr, uid, eval(domain), context=context)
            self.pool['mail.mass_mailing.contact'].write(cr, uid, contact_ids, {'list_id': new_id}, context=context)
            self.pool['mail.mass_mailing.list'].write(cr, uid, [new_id], {'domain': [('list_id', '=', new_id)]}, context=context)
        return new_id

    def action_see_records(self, cr, uid, ids, context=None):
        contact_list = self.browse(cr, uid, ids[0], context=context)
        ctx = dict(context)
        ctx['search_default_not_opt_out'] = True
        return {
            'name': _('See Contact List'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': contact_list.model,
            'views': [(False, 'tree'), (False, 'form')],
            'view_id': False,
            'target': 'current',
            'context': ctx,
            'domain': contact_list.domain,
        }

    def action_add_to_mailing(self, cr, uid, ids, context=None):
        mass_mailing_id = context.get('default_mass_mailing_id')
        if not mass_mailing_id:
            return False
        self.pool['mail.mass_mailing'].write(cr, uid, [mass_mailing_id], {'contact_list_ids': [(4, list_id) for list_id in ids]}, context=context)
        return {
            'name': _('Mass Mailing'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.mass_mailing',
            'res_id': mass_mailing_id,
            'context': context,
        }

    def _get_domain(self, cr, uid, ids, context=None):
        domains = {}
        for contact_list in self.browse(cr, uid, ids, context=context):
            if contact_list.domain is False or contact_list.domain is None:  # domain is a string like False or None -> void list
                domain = [('id', '=', '0')]
            else:
                domain = eval(contact_list.domain)
            domains[contact_list.id] = domain
        return domains

    def get_global_domain(self, cr, uid, ids, context=None):
        model_to_domains = dict((mailing_model[0], list())
                                for mailing_model in self.pool['mail.mass_mailing']._get_mailing_model(cr, uid, context=context))
        for contact_list in self.browse(cr, uid, ids, context=context):
            domain = self._get_domain(cr, uid, [contact_list.id], context=context)[contact_list.id]
            if domain is not False:
                model_to_domains[contact_list.model].append(domain)
        for model, domains in model_to_domains.iteritems():
            if domains:
                final_domain = ['|'] * (len(domains) - 1) + [leaf for dom in domains for leaf in dom]
            else:
                final_domain = [('id', '=', '0')]
            model_to_domains[model] = final_domain
        return model_to_domains


class MassMailingStage(osv.Model):
    """Stage for mass mailing campaigns. """
    _name = 'mail.mass_mailing.stage'
    _description = 'Mass Mailing Campaign Stage'
    _order = 'sequence ASC'

    _columns = {
        'name': fields.char('Name', required=True),
        'sequence': fields.integer('Sequence'),
    }

    _defaults = {
        'sequence': 0,
    }


class MassMailingCampaign(osv.Model):
    """Model of mass mailing campaigns. """
    _name = "mail.mass_mailing.campaign"
    _description = 'Mass Mailing Campaign'

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
        'name': fields.char('Name', required=True),
        'stage_id': fields.many2one('mail.mass_mailing.stage', 'Stage', required=True),
        'user_id': fields.many2one(
            'res.users', 'Responsible',
            required=True,
        ),
        'category_id': fields.many2one(
            'mail.mass_mailing.category', 'Category',
            help='Category'),
        'mass_mailing_ids': fields.one2many(
            'mail.mass_mailing', 'mass_mailing_campaign_id',
            'Mass Mailings',
        ),
        'ab_testing': fields.boolean(
            'AB Testing',
            help='If checked, recipients will be mailed only once, allowing to send'
                 'various mailings in a single campaign to test the effectiveness'
                 'of the mailings.'),
        'color': fields.integer('Color Index'),
        # stat fields
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

    def _get_default_stage_id(self, cr, uid, context=None):
        stage_ids = self.pool['mail.mass_mailing.stage'].search(cr, uid, [], limit=1, context=context)
        return stage_ids and stage_ids[0]

    _defaults = {
        'user_id': lambda self, cr, uid, ctx=None: uid,
        'stage_id': lambda self, cr, uid, ctx=None: self._get_default_stage_id(cr, uid, context=ctx),
    }

    #------------------------------------------------------
    # Actions
    #------------------------------------------------------

    def action_new_mailing(self, cr, uid, ids, context=None):
        return {
            'name': _('Create a Mass Mailing for the Campaign'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.mass_mailing',
            'views': [(False, 'form')],
            'context': dict(context, default_mass_mailing_campaign_id=ids[0]),
        }

    #------------------------------------------------------
    # API
    #------------------------------------------------------

    def get_recipients(self, cr, uid, ids, model=None, context=None):
        """Return the recipints of a mailing campaign. This is based on the statistics
        build for each mailing. """
        Statistics = self.pool['mail.mail.statistics']
        res = dict.fromkeys(ids, False)
        for cid in ids:
            domain = [('mass_mailing_campaign_id', '=', cid)]
            if model:
                domain += [('model', '=', model)]
            stat_ids = Statistics.search(cr, uid, domain, context=context)
            res[cid] = set(stat.res_id for stat in Statistics.browse(cr, uid, stat_ids, context=context))
        return res


class MassMailing(osv.Model):
    """ MassMailing models a wave of emails for a mass mailign campaign.
    A mass mailing is an occurence of sending emails. """

    _name = 'mail.mass_mailing'
    _description = 'Mass Mailing'
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

    def _get_contact_nbr(self, cr, uid, ids, name, arg, context=None):
        res = dict.fromkeys(ids, False)
        for mailing in self.browse(cr, uid, ids, context=context):
            val = {'contact_nbr': 0, 'contact_ab_nbr': 0, 'contact_ab_done': 0}
            val['contact_nbr'] = self.pool[mailing.mailing_model].search(
                cr, uid,
                self.pool['mail.mass_mailing.list'].get_global_domain(cr, uid, [c.id for c in mailing.contact_list_ids], context=context)[mailing.mailing_model],
                count=True, context=context
            )
            val['contact_ab_nbr'] = int(val['contact_nbr'] * mailing.contact_ab_pc / 100.0)
            if mailing.mass_mailing_campaign_id and mailing.ab_testing:
                val['contact_ab_done'] = len(self.pool['mail.mass_mailing.campaign'].get_recipients(cr, uid, [mailing.mass_mailing_campaign_id.id], context=context)[mailing.mass_mailing_campaign_id.id])
            res[mailing.id] = val
        return res

    def _get_private_models(self, context=None):
        return ['res.partner', 'mail.mass_mailing.contact']

    def _get_auto_reply_to_available(self, cr, uid, ids, name, arg, context=None):
        res = dict.fromkeys(ids, False)
        for mailing in self.browse(cr, uid, ids, context=context):
            res[mailing.id] = mailing.mailing_model not in self._get_private_models(context=context)
        return res

    def _get_mailing_model(self, cr, uid, context=None):
        return [
            ('res.partner', 'Customers'),
            ('mail.mass_mailing.contact', 'Contacts')
        ]

    def _get_state_list(self, cr, uid, context=None):
        return [('draft', 'Schedule'), ('test', 'Tested'), ('done', 'Sent')]

    # indirections for inheritance
    _mailing_model = lambda self, *args, **kwargs: self._get_mailing_model(*args, **kwargs)
    _state = lambda self, *args, **kwargs: self._get_state_list(*args, **kwargs)

    _columns = {
        'name': fields.char('Subject', required=True),
        'date': fields.datetime('Date'),
        'state': fields.selection(
            _state, string='Status', required=True,
        ),
        'template_id': fields.many2one(
            'email.template', 'Email Template',
            domain="[('use_in_mass_mailing', '=', True), ('model', '=', mailing_model)]",
        ),
        'body_html': fields.html('Body'),
        'mass_mailing_campaign_id': fields.many2one(
            'mail.mass_mailing.campaign', 'Mass Mailing Campaign',
            ondelete='set null',
        ),
        'ab_testing': fields.related(
            'mass_mailing_campaign_id', 'ab_testing',
            type='boolean', string='AB Testing'
        ),
        'color': fields.related(
            'mass_mailing_campaign_id', 'color',
            type='integer', string='Color Index',
        ),
        # mailing options
        'email_from': fields.char('From'),
        'reply_in_thread': fields.boolean('Reply in thread'),
        'reply_specified': fields.boolean('Specific Reply-To'),
        'auto_reply_to_available': fields.function(
            _get_auto_reply_to_available,
            type='boolean', string='Reply in thread available'
        ),
        'reply_to': fields.char('Reply To'),
        'mailing_model': fields.selection(_mailing_model, string='Type', required=True),
        'contact_list_ids': fields.many2many(
            'mail.mass_mailing.list', 'mail_mass_mailing_list_rel',
            string='Mailing Lists',
            domain="[('model', '=', mailing_model)]",
        ),
        'contact_nbr': fields.function(
            _get_contact_nbr, type='integer', multi='_get_contact_nbr',
            string='Contact Number'
        ),
        'contact_ab_pc': fields.integer(
            'AB Testing percentage',
            help='Percentage of the contacts that will be mailed. Recipients will be taken randomly.'
        ),
        'contact_ab_nbr': fields.function(
            _get_contact_nbr, type='integer', multi='_get_contact_nbr',
            string='Contact Number in AB Testing'
        ),
        'contact_ab_done': fields.function(
            _get_contact_nbr, type='integer', multi='_get_contact_nbr',
            string='Number of already mailed contacts'
        ),
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

    _defaults = {
        'state': 'draft',
        'date': fields.datetime.now,
        'email_from': lambda self, cr, uid, ctx=None: self.pool['mail.message']._get_default_from(cr, uid, context=ctx),
        'mailing_model': 'res.partner',
        'contact_ab_pc': 100,
    }

    #------------------------------------------------------
    # Technical stuff
    #------------------------------------------------------

    def copy_data(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        mailing = self.browse(cr, uid, id, context=context)
        default.update({
            'state': 'draft',
            'statistics_ids': [],
            'state': 'draft',
            'name': _('%s (duplicate)') % mailing.name,
        })
        return super(MassMailing, self).copy_data(cr, uid, id, default, context=context)

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
        """ Override read_group to always display all states. """
        if groupby and groupby[0] == "state":
            # Default result structure
            states = self._get_state_list(cr, uid, context=context)
            read_group_all_states = [{
                '__context': {'group_by': groupby[1:]},
                '__domain': domain + [('state', '=', state_value)],
                'state': state_value,
                'state_count': 0,
            } for state_value, state_name in states]
            # Get standard results
            read_group_res = super(MassMailing, self).read_group(cr, uid, domain, fields, groupby, offset=offset, limit=limit, context=context, orderby=orderby)
            # Update standard results with default results
            result = []
            for state_value, state_name in states:
                res = filter(lambda x: x['state'] == state_value, read_group_res)
                if not res:
                    res = filter(lambda x: x['state'] == state_value, read_group_all_states)
                res[0]['state'] = [state_value, state_name]
                result.append(res[0])
            return result
        else:
            return super(MassMailing, self).read_group(cr, uid, domain, fields, groupby, offset=offset, limit=limit, context=context, orderby=orderby)

    #------------------------------------------------------
    # Views & Actions
    #------------------------------------------------------

    def on_change_mailing_model(self, cr, uid, ids, mailing_model, context=None):
        values = {
            'contact_list_ids': [],
            'template_id': False,
            'contact_nbr': 0,
            'auto_reply_to_available': not mailing_model in self._get_private_models(context),
            'reply_in_thread': not mailing_model in self._get_private_models(context),
            'reply_specified': mailing_model in self._get_private_models(context)
        }
        return {'value': values}

    def on_change_reply_specified(self, cr, uid, ids, reply_specified, reply_in_thread, context=None):
        if reply_specified == reply_in_thread:
            return {'value': {'reply_in_thread': not reply_specified}}
        return {}

    def on_change_reply_in_thread(self, cr, uid, ids, reply_specified, reply_in_thread, context=None):
        if reply_in_thread == reply_specified:
            return {'value': {'reply_specified': not reply_in_thread}}
        return {}

    def on_change_contact_list_ids(self, cr, uid, ids, mailing_model, contact_list_ids, context=None):
        values = {}
        list_ids = []
        for command in contact_list_ids:
            if command[0] == 6:
                list_ids += command[2]
        if list_ids:
            values['contact_nbr'] = self.pool[mailing_model].search(
                cr, uid,
                self.pool['mail.mass_mailing.list'].get_global_domain(cr, uid, list_ids, context=context)[mailing_model],
                count=True, context=context
            )
        return {'value': values}

    def on_change_template_id(self, cr, uid, ids, template_id, context=None):
        values = {}
        if template_id:
            template = self.pool['email.template'].browse(cr, uid, template_id, context=context)
            if template.email_from:
                values['email_from'] = template.email_from
            if template.reply_to:
                values['reply_to'] = template.reply_to
            values['body_html'] = template.body_html
        else:
            values['email_from'] = self.pool['mail.message']._get_default_from(cr, uid, context=context)
            values['reply_to'] = False
            values['body_html'] = False
        return {'value': values}

    def on_change_contact_ab_pc(self, cr, uid, ids, contact_ab_pc, contact_nbr, context=None):
        return {'value': {'contact_ab_nbr': contact_nbr * contact_ab_pc / 100.0}}

    def action_duplicate(self, cr, uid, ids, context=None):
        copy_id = None
        for mid in ids:
            copy_id = self.copy(cr, uid, mid, context=context)
        if copy_id:
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'mail.mass_mailing',
                'res_id': copy_id,
                'context': context,
            }
        return False

    def _get_model_to_list_action_id(self, cr, uid, model, context=None):
        if model == 'res.partner':
            return self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'mass_mailing.action_partner_to_mailing_list')
        else:
            return self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'mass_mailing.action_contact_to_mailing_list')

    def action_new_list(self, cr, uid, ids, context=None):
        mailing = self.browse(cr, uid, ids[0], context=context)
        action_id = self._get_model_to_list_action_id(cr, uid, mailing.mailing_model, context=context)
        ctx = dict(context,
                   search_default_not_opt_out=True,
                   view_manager_highlight=[action_id],
                   default_name=mailing.name,
                   default_mass_mailing_id=ids[0],
                   default_model=mailing.mailing_model)
        return {
            'name': _('Choose Recipients'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': mailing.mailing_model,
            'context': ctx,
        }

    def action_see_recipients(self, cr, uid, ids, context=None):
        mailing = self.browse(cr, uid, ids[0], context=context)
        domain = self.pool['mail.mass_mailing.list'].get_global_domain(cr, uid, [c.id for c in mailing.contact_list_ids], context=context)[mailing.mailing_model]
        return {
            'name': _('See Recipients'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': mailing.mailing_model,
            'target': 'new',
            'domain': domain,
            'context': context,
        }

    def action_test_mailing(self, cr, uid, ids, context=None):
        ctx = dict(context, default_mass_mailing_id=ids[0])
        return {
            'name': _('Test Mailing'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.mass_mailing.test',
            'target': 'new',
            'context': ctx,
        }

    def action_edit_html(self, cr, uid, ids, context=None):
        url = '/website_mail/email_designer?model=mail.mass_mailing&res_id=%d' % ids[0]
        return {
            'name': _('Open with Visual Editor'),
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
        }

    #------------------------------------------------------
    # Email Sending
    #------------------------------------------------------

    def get_recipients_data(self, cr, uid, mailing, res_ids, context=None):
        # tde todo: notification link ?
        if mailing.mailing_model == 'mail.mass_mailing.contact':
            contacts = self.pool['mail.mass_mailing.contact'].browse(cr, uid, res_ids, context=context)
            return dict((contact.id, {'partner_id': False, 'name': contact.name, 'email': contact.email}) for contact in contacts)
        else:
            partners = self.pool['res.partner'].browse(cr, uid, res_ids, context=context)
            return dict((partner.id, {'partner_id': partner.id, 'name': partner.name, 'email': partner.email}) for partner in partners)

    def get_recipients(self, cr, uid, mailing, context=None):
        domain = self.pool['mail.mass_mailing.list'].get_global_domain(
            cr, uid, [l.id for l in mailing.contact_list_ids], context=context
        )[mailing.mailing_model]
        res_ids = self.pool[mailing.mailing_model].search(cr, uid, domain, context=context)

        # randomly choose a fragment
        if mailing.contact_ab_pc != 100:
            topick = mailing.contact_ab_nbr
            if mailing.mass_mailing_campaign_id and mailing.ab_testing:
                already_mailed = self.pool['mail.mass_mailing.campaign'].get_recipients(cr, uid, [mailing.mass_mailing_campaign_id.id], context=context)[mailing.mass_mailing_campaign_id.id]
            else:
                already_mailed = set([])
            remaining = set(res_ids).difference(already_mailed)
            if topick > len(remaining):
                topick = len(remaining)
            res_ids = random.sample(remaining, topick)
        return res_ids

    def get_unsubscribe_url(self, cr, uid, mailing_id, res_id, email, msg=None, context=None):
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        url = urlparse.urljoin(
            base_url, 'mail/mailing/%(mailing_id)s/unsubscribe?%(params)s' % {
                'mailing_id': mailing_id,
                'params': urllib.urlencode({'db': cr.dbname, 'res_id': res_id, 'email': email})
            }
        )
        return '<small><a href="%s">%s</a></small>' % (url, msg or 'Click to unsubscribe')

    def send_mail(self, cr, uid, ids, context=None):
        author_id = self.pool['res.users'].browse(cr, uid, uid, context=context).partner_id.id
        for mailing in self.browse(cr, uid, ids, context=context):
            if not mailing.contact_nbr:
                raise Warning('Please select recipients.')
            # instantiate an email composer + send emails
            res_ids = self.get_recipients(cr, uid, mailing, context=context)
            comp_ctx = dict(context, active_ids=res_ids)
            composer_values = {
                'author_id': author_id,
                'body': mailing.body_html,
                'subject': mailing.name,
                'model': mailing.mailing_model,
                'email_from': mailing.email_from,
                'record_name': False,
                'composition_mode': 'mass_mail',
                'mass_mailing_id': mailing.id,
                'mailing_list_ids': [(4, l.id) for l in mailing.contact_list_ids],
            }
            if mailing.reply_specified:
                composer_values['reply_to'] = mailing.reply_to
            composer_id = self.pool['mail.compose.message'].create(cr, uid, composer_values, context=comp_ctx)
            self.pool['mail.compose.message'].send_mail(cr, uid, [composer_id], context=comp_ctx)
            self.write(cr, uid, [mailing.id], {'date': fields.datetime.now(), 'state': 'done'}, context=context)
        return True


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
        'template_id': fields.related(
            'mass_mailing_id', 'template_id',
            type='many2one', ondelete='set null',
            relation='email.template',
            string='Email Template',
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
