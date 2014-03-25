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
            res['model'] = context.get('active_model', 'res.partner')
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
        # contact-based list
        'contact_ids': fields.one2many(
            'mail.mass_mailing.contact', 'list_id', string='Contacts',
            domain=[('opt_out', '=', False)],
        ),
        # filter-based list
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
        values = {}
        if model == 'mail.mass_mailing.contact':
            values.update(domain=False, filter_id=False, template_id=False)
        else:
            values.update(filter_id=False, template_id=False)
        return {'value': values}

    def on_change_filter_id(self, cr, uid, ids, filter_id, context=None):
        values = {}
        if filter_id:
            ir_filter = self.pool['ir.filters'].browse(cr, uid, filter_id, context=context)
            values['domain'] = ir_filter.domain
        else:
            values['domain'] = False
        return {'value': values}

    def on_change_domain(self, cr, uid, ids, domain, model, context=None):
        if domain is False:
            return {'value': {'contact_nbr': 0}}
        else:
            domain = eval(domain)
            return {'value': {'contact_nbr': self.pool[model].search(cr, uid, domain, context=context, count=True)}}

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
            'name': _('New Mass Mailing'),
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
            if contact_list.model == 'mail.mass_mailing.contact':
                domain = [('list_id', '=', contact_list.id)]
            elif not contact_list.domain:  # domain is a string like False or None -> void list
                domain = [('id', '=', '0')]
            else:
                domain = eval(contact_list.domain)
            # force the addition of opt_out filter
            if domain:
                domain = ['&', ('opt_out', '=', False)] + domain
            else:
                domain = [('opt_out', '=', False)]
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


class MassMailingCampaign(osv.Model):
    """Model of mass mailing campaigns. """
    _name = "mail.mass_mailing.campaign"
    _description = 'Mass Mailing Campaign'
    # number of embedded mailings in kanban view
    _kanban_mailing_nbr = 4

    def _get_statistics(self, cr, uid, ids, name, arg, context=None):
        """ Compute statistics of the mass mailing campaign """
        Statistics = self.pool['mail.mail.statistics']
        results = dict.fromkeys(ids, False)
        for cid in ids:
            results[cid] = {
                'total': Statistics.search(cr, uid, [('mass_mailing_campaign_id', '=', cid)], count=True, context=context),
                'sent': Statistics.search(cr, uid, [('mass_mailing_campaign_id', '=', cid), ('sent', '!=', False)], count=True, context=context),
                'opened': Statistics.search(cr, uid, [('mass_mailing_campaign_id', '=', cid), ('opened', '!=', False)], count=True, context=context),
                'replied': Statistics.search(cr, uid, [('mass_mailing_campaign_id', '=', cid), ('replied', '!=', False)], count=True, context=context),
                'bounced': Statistics.search(cr, uid, [('mass_mailing_campaign_id', '=', cid), ('bounced', '!=', False)], count=True, context=context),
            }
            results[cid]['delivered'] = results[cid]['sent'] - results[cid]['bounced']
        return results

    def _get_state_list(self, cr, uid, context=None):
        return [('draft', 'Schedule'), ('design', 'Design'), ('done', 'Sent')]

    # indirections for inheritance
    _state = lambda self, *args, **kwargs: self._get_state_list(*args, **kwargs)

    _columns = {
        'name': fields.char('Name', required=True),
        'state': fields.selection(_state, string='Status', required=True),
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
        'statistics_ids': fields.one2many(
            'mail.mail.statistics', 'mass_mailing_campaign_id',
            'Sent Emails',
        ),
        'color': fields.integer('Color Index'),
        # stat fields
        'total': fields.function(
            _get_statistics, string='Scheduled',
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
    }

    _defaults = {
        'user_id': lambda self, cr, uid, ctx=None: uid,
        'state': 'draft',
    }

    #------------------------------------------------------
    # Technical stuff
    #------------------------------------------------------

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False):
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
            read_group_res = super(MassMailingCampaign, self).read_group(cr, uid, domain, fields, groupby, offset=offset, limit=limit, context=context, orderby=orderby)
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
            return super(MassMailingCampaign, self).read_group(cr, uid, domain, fields, groupby, offset=offset, limit=limit, context=context, orderby=orderby)

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
            res[id]['opened_dayly'] = self.__get_bar_values(cr, uid, id, obj, domain, ['opened'], 'opened_count', 'opened:day', context=context)
            domain = [('mass_mailing_id', '=', id), ('replied', '>=', date_begin_str), ('replied', '<=', date_end_str)]
            res[id]['replied_dayly'] = self.__get_bar_values(cr, uid, id, obj, domain, ['replied'], 'replied_count', 'replied:day', context=context)
        return res

    def _get_statistics(self, cr, uid, ids, name, arg, context=None):
        """ Compute statistics of the mass mailing campaign """
        Statistics = self.pool['mail.mail.statistics']
        results = dict.fromkeys(ids, False)
        for mid in ids:
            results[mid] = {
                'total': Statistics.search(cr, uid, [('mass_mailing_id', '=', mid)], count=True, context=context),
                'sent': Statistics.search(cr, uid, [('mass_mailing_id', '=', mid), ('sent', '!=', False)], count=True, context=context),
                'opened': Statistics.search(cr, uid, [('mass_mailing_id', '=', mid), ('opened', '!=', False)], count=True, context=context),
                'replied': Statistics.search(cr, uid, [('mass_mailing_id', '=', mid), ('replied', '!=', False)], count=True, context=context),
                'bounced': Statistics.search(cr, uid, [('mass_mailing_id', '=', mid), ('bounced', '!=', False)], count=True, context=context),
            }
            results[mid]['delivered'] = results[mid]['sent'] - results[mid]['bounced']
        return results

    def _get_contact_nbr(self, cr, uid, ids, name, arg, context=None):
        res = dict.fromkeys(ids, 0)
        for mailing in self.browse(cr, uid, ids, context=context):
            res[mailing.id] = self.pool[mailing.mailing_model].search(
                cr, uid,
                self.pool['mail.mass_mailing.list'].get_global_domain(cr, uid, [c.id for c in mailing.contact_list_ids], context=context)[mailing.mailing_model],
                count=True, context=context
            )
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
        'body_html': fields.related(
            'template_id', 'body_html', type='html',
            string='Body', readonly='True',
            help='Technical field: used only to display a view of the template in the form view',
        ),
        'mass_mailing_campaign_id': fields.many2one(
            'mail.mass_mailing.campaign', 'Mass Mailing Campaign',
            ondelete='set null',
        ),
        'color': fields.related(
            'mass_mailing_campaign_id', 'color',
            type='integer', string='Color Index',
        ),
        # mailing options
        'email_from': fields.char('From'),
        'email_to': fields.many2many(
            'mail.mass_mailing.contact', 'mail_mass_mailing_contact_rel',
            string='Test Emails'
        ),
        'reply_to': fields.char('Reply To'),
        'mailing_model': fields.selection(_mailing_model, string='Type', required=True),
        'contact_list_ids': fields.many2many(
            'mail.mass_mailing.list', 'mail_mass_mailing_list_rel',
            string='Mailing Lists',
            domain="[('model', '=', mailing_model)]",
        ),
        'contact_nbr': fields.function(_get_contact_nbr, type='integer', string='Contact Number'),
        # statistics data
        'statistics_ids': fields.one2many(
            'mail.mail.statistics', 'mass_mailing_id',
            'Emails Statistics',
        ),
        'total': fields.function(
            _get_statistics, string='Scheduled',
            type='integer', multi='_get_statistics'
        ),
        'sent': fields.function(
            _get_statistics, string='Sent',
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
        # monthly ratio
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
    }

    #------------------------------------------------------
    # Technical stuff
    #------------------------------------------------------

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False):
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
        return {'value': {'contact_list_ids': [], 'template_id': False, 'contact_nbr': 0}}

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

    def _get_model_to_list_action_id(self, cr, uid, model, context=None):
        if model == 'res.partner':
            return self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'mass_mailing.action_partner_to_mailing_list')
        else:
            return self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'mass_mailing.action_contact_to_mailing_list')

    def action_duplicate(self, cr, uid, ids, context=None):
        copy_id = None
        for mailing in self.browse(cr, uid, ids, context=context):
            copy_id = self.copy(
                cr, uid, mailing.id, default={
                    'statistics_ids': [],
                    'state': 'draft',
                    'name': _('%s (duplicate)') % mailing.name,
                }, context=context)
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

    def action_new_list(self, cr, uid, ids, context=None):
        wizard = self.browse(cr, uid, ids[0], context=context)
        action_id = self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'mass_mailing.action_partner_to_mailing_list')
        ctx = dict(context, view_manager_highlight=[action_id], default_mass_mailing_id=ids[0])
        return {
            'name': _('Choose Recipients'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': wizard.mailing_model,
            'context': ctx,
        }

    def action_see_recipients(self, cr, uid, ids, context=None):
        mailing = self.browse(cr, uid, ids[0], context=context)
        domain = self.pool['mail.mass_mailing.list'].get_global_domain(cr, uid, [c.id for c in mailing.contact_list_ids], context=context)[mailing.mailing_model]
        return {
            'name': _('Mailing Recipients'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': mailing.mailing_model,
            'target': 'new',
            'domain': domain,
            'context': context,
        }

    def action_template_new(self, cr, uid, ids, context=None):
        mailing = self.browse(cr, uid, ids[0], context=context)
        view_id = self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'email_template.email_template_form_minimal')
        ctx = dict(
            context,
            default_model=mailing.mailing_model,
            default_use_in_mass_mailing=True,
            default_use_default_to=True,
            default_name=mailing.name,
        )
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'email.template',
            'view_id': view_id,
            'context': ctx,
        }

    def action_template_copy(self, cr, uid, ids, context=None):
        mailing = self.browse(cr, uid, ids[0], context=context)
        if not mailing.template_id:
            return False
        new_tpl_id = self.pool['email.template'].copy(cr, uid, mailing.template_id.id, context=context)
        self.write(cr, uid, [mailing.id], {'template_id': new_tpl_id}, context=context)
        view_id = self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'email_template.email_template_form_minimal')
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'email.template',
            'res_id': new_tpl_id,
            'view_id': view_id,
            'target': 'new',
            'context': context,
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

    def get_unsubscribe_url(self, cr, uid, mailing, res_id, email, msg=None, context=None):
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        url = urlparse.urljoin(
            base_url, 'mail/mailing/%(mailing_id)s/unsubscribe?%(params)s' % {
                'mailing_id': mailing.id,
                'params': urllib.urlencode({'res_id': res_id, 'email': email})
            }
        )
        return '<a href="%s">%s</a>' % (url, msg or 'Click to unsubscribe')

    def send_mail(self, cr, uid, ids, context=None):
        author_id = self.pool['res.users'].browse(cr, uid, uid, context=context).partner_id.id
        Mail = self.pool['mail.mail']
        for mailing in self.browse(cr, uid, ids, context=context):
            if not mailing.template_id:
                raise Warning('Please specifiy a template to use.')
            if not mailing.contact_nbr:
                raise Warning('Please select recipients.')

            # get mail and recipints data
            domain = self.pool['mail.mass_mailing.list'].get_global_domain(
                cr, uid, [l.id for l in mailing.contact_list_ids], context=context
            )[mailing.mailing_model]
            res_ids = self.pool[mailing.mailing_model].search(cr, uid, domain, context=context)
            template_values = self.pool['mail.compose.message'].generate_email_for_composer_batch(
                cr, uid, mailing.template_id.id, res_ids,
                context=context, fields=['body_html', 'attachment_ids', 'mail_server_id'])
            recipient_values = self.get_recipients_data(cr, uid, mailing, res_ids, context=context)

            for res_id, mail_values in template_values.iteritems():
                body = mail_values.get('body')
                recipient = recipient_values[res_id]
                unsubscribe_url = self.get_unsubscribe_url(cr, uid, mailing, res_id, recipient['email'], context=context)
                if unsubscribe_url:
                    body = tools.append_content_to_html(body, unsubscribe_url, plaintext=False, container_tag='p')

                mail_values.update({
                    'email_from': mailing.email_from,
                    'reply_to': mailing.reply_to,
                    'subject': mailing.name,
                    'record_name': False,
                    'author_id': author_id,
                    'body_html': body,
                    'auto_delete': True,
                    'notification': True,
                    'email_to': '"%s" <%s>' % (recipient['name'], recipient['email'])
                })
                mail_values['statistics_ids'] = [
                    (0, 0, {
                        'model': mailing.mailing_model,
                        'res_id': res_id,
                        'mass_mailing_id': mailing.id,
                    })]
                m2m_attachment_ids = self.pool['mail.thread']._message_preprocess_attachments(
                    cr, uid, mail_values.pop('attachments', []),
                    mail_values.pop('attachment_ids', []),
                    'mail.message', 0,
                    context=context)
                mail_values['attachment_ids'] = m2m_attachment_ids

                Mail.create(cr, uid, mail_values, context=context)
        return True

    def send_mail_test(self, cr, uid, ids, context=None):
        Mail = self.pool['mail.mail']
        for mailing in self.browse(cr, uid, ids, context=context):
            if not mailing.template_id:
                raise Warning('Please specifiy a template to use.')
            # res_ids = self._set_up_test_mailing(cr, uid, mailing.mailing_model, context=context)
            res_ids = [c.id for c in mailing.email_to]
            if not res_ids:
                raise Warning('Please specifiy test email adresses.')
            all_mail_values = self.pool['mail.compose.message'].generate_email_for_composer_batch(
                cr, uid, mailing.template_id.id, res_ids,
                context=context,
                fields=['body_html', 'attachment_ids', 'mail_server_id']
            )
            mail_ids = []
            for res_id, mail_values in all_mail_values.iteritems():
                mail_values = {
                    'email_from': mailing.email_from,
                    'reply_to': mailing.reply_to,
                    'email_to': self.pool['mail.mass_mailing.contact'].browse(cr, uid, res_id, context=context).email,
                    'subject': mailing.name,
                    'body_html': mail_values.get('body'),
                    'auto_delete': True,
                }
                mail_ids.append(Mail.create(cr, uid, mail_values, context=context))
            Mail.send(cr, uid, mail_ids, context=context)
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
        'sent': fields.datetime(
            'Sent',
            help='Date the related email was sent'),
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
            ids = self.search(cr, uid, [('mail_mail_id', 'in', mail_mail_ids), ('opened', '=', False)], context=context)
        elif not ids and mail_message_ids:
            ids = self.search(cr, uid, [('message_id', 'in', mail_message_ids), ('opened', '=', False)], context=context)
        else:
            ids = self.search(cr, uid, [('id', 'in', ids or []), ('opened', '=', False)], context=context)
        return self.write(cr, uid, ids, {'opened': fields.datetime.now()}, context=context)

    def set_replied(self, cr, uid, ids=None, mail_mail_ids=None, mail_message_ids=None, context=None):
        """ Set as replied """
        if not ids and mail_mail_ids:
            ids = self.search(cr, uid, [('mail_mail_id', 'in', mail_mail_ids), ('replied', '=', False)], context=context)
        elif not ids and mail_message_ids:
            ids = self.search(cr, uid, [('message_id', 'in', mail_message_ids), ('replied', '=', False)], context=context)
        else:
            ids = self.search(cr, uid, [('id', 'in', ids or []), ('replied', '=', False)], context=context)
        return self.write(cr, uid, ids, {'replied': fields.datetime.now()}, context=context)

    def set_bounced(self, cr, uid, ids=None, mail_mail_ids=None, mail_message_ids=None, context=None):
        """ Set as bounced """
        if not ids and mail_mail_ids:
            ids = self.search(cr, uid, [('mail_mail_id', 'in', mail_mail_ids), ('bounced', '=', False)], context=context)
        elif not ids and mail_message_ids:
            ids = self.search(cr, uid, [('message_id', 'in', mail_message_ids), ('bounced', '=', False)], context=context)
        else:
            ids = self.search(cr, uid, [('id', 'in', ids or []), ('bounced', '=', False)], context=context)
        return self.write(cr, uid, ids, {'bounced': fields.datetime.now()}, context=context)
