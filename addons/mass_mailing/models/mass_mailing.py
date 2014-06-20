# -*- coding: utf-8 -*-

from datetime import datetime
from dateutil import relativedelta
import json
import random

from openerp import tools
from openerp.exceptions import Warning
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools.translate import _
from openerp.osv import osv, fields


class MassMailingCategory(osv.Model):
    """Model of categories of mass mailing, i.e. marketing, newsletter, ... """
    _name = 'mail.mass_mailing.category'
    _description = 'Mass Mailing Category'
    _order = 'name'

    _columns = {
        'name': fields.char('Name', required=True),
    }


class MassMailingContact(osv.Model):
    """Model of a contact. This model is different from the partner model
    because it holds only some basic information: name, email. The purpose is to
    be able to deal with large contact list to email without bloating the partner
    base."""
    _name = 'mail.mass_mailing.contact'
    _description = 'Mass Mailing Contact'
    _order = 'email'
    _rec_name = 'email'

    _columns = {
        'name': fields.char('Name'),
        'email': fields.char('Email', required=True),
        'create_date': fields.datetime('Create Date'),
        'list_id': fields.many2one(
            'mail.mass_mailing.list', string='Mailing List',
            ondelete='cascade', required=True,
        ),
        'opt_out': fields.boolean('Opt Out', help='The contact has chosen not to receive mails anymore from this list'),
    }

    def _get_latest_list(self, cr, uid, context={}):
        lid = self.pool.get('mail.mass_mailing.list').search(cr, uid, [], limit=1, order='id desc', context=context)
        return lid and lid[0] or False

    _defaults = {
        'list_id': _get_latest_list
    }

    def name_create(self, cr, uid, name, context=None):
        name, email = self.pool['res.partner']._parse_partner_name(name, context=context)
        if name and not email:
            email = name
        if email and not name:
            name = email
        rec_id = self.create(cr, uid, {'name': name, 'email': email}, context=context)
        return self.name_get(cr, uid, [rec_id], context)[0]

    def message_get_default_recipients(self, cr, uid, ids, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = {'partner_ids': [], 'email_to': record.email, 'email_cc': False}
        return res


class MassMailingList(osv.Model):
    """Model of a contact list. """
    _name = 'mail.mass_mailing.list'
    _order = 'name'
    _description = 'Mailing List'

    def _get_contact_nbr(self, cr, uid, ids, name, arg, context=None):
        result = dict.fromkeys(ids, 0)
        Contacts = self.pool.get('mail.mass_mailing.contact')
        for group in Contacts.read_group(cr, uid, [('list_id', 'in', ids), ('opt_out', '!=', True)], ['list_id'], ['list_id'], context=context):
            result[group['list_id'][0]] = group['list_id_count']
        return result

    _columns = {
        'name': fields.char('Mailing List', required=True),
        'contact_nbr': fields.function(
            _get_contact_nbr, type='integer',
            string='Number of Contacts',
        ),
    }


class MassMailingStage(osv.Model):
    """Stage for mass mailing campaigns. """
    _name = 'mail.mass_mailing.stage'
    _description = 'Mass Mailing Campaign Stage'
    _order = 'sequence'

    _columns = {
        'name': fields.char('Name', required=True, translate=True),
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
            results[cid]['received_ratio'] = 100.0 * results[cid]['delivered'] / (results[cid]['total'] or 1)
            results[cid]['opened_ratio'] = 100.0 * results[cid]['opened'] / (results[cid]['total'] or 1)
            results[cid]['replied_ratio'] = 100.0 * results[cid]['replied'] / (results[cid]['total'] or 1)
        return results

    _columns = {
        'name': fields.char('Name', required=True),
        'stage_id': fields.many2one('mail.mass_mailing.stage', 'Stage', required=True),
        'user_id': fields.many2one(
            'res.users', 'Responsible',
            required=True,
        ),
        'category_ids': fields.many2many(
            'mail.mass_mailing.category', 'mail_mass_mailing_category_rel',
            'category_id', 'campaign_id', string='Categories'),
        'mass_mailing_ids': fields.one2many(
            'mail.mass_mailing', 'mass_mailing_campaign_id',
            'Mass Mailings',
        ),
        'unique_ab_testing': fields.boolean(
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
        return stage_ids and stage_ids[0] or False

    _defaults = {
        'user_id': lambda self, cr, uid, ctx=None: uid,
        'stage_id': lambda self, *args: self._get_default_stage_id(*args),
    }

    def get_recipients(self, cr, uid, ids, model=None, context=None):
        """Return the recipients of a mailing campaign. This is based on the statistics
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
    _order = 'sent_date DESC'

    def __get_bar_values(self, cr, uid, obj, domain, read_fields, value_field, groupby_field, date_begin, context=None):
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
        date_begin = date_begin.date()
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
        for mailing in self.browse(cr, uid, ids, context=context):
            res[mailing.id] = {}
            date = mailing.sent_date if mailing.sent_date else mailing.create_date
            date_begin = datetime.strptime(date, tools.DEFAULT_SERVER_DATETIME_FORMAT)
            date_end = date_begin + relativedelta.relativedelta(days=self._period_number - 1)
            date_begin_str = date_begin.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
            date_end_str = date_end.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
            domain = [('mass_mailing_id', '=', mailing.id), ('opened', '>=', date_begin_str), ('opened', '<=', date_end_str)]
            res[mailing.id]['opened_daily'] = json.dumps(self.__get_bar_values(cr, uid, obj, domain, ['opened'], 'opened_count', 'opened:day', date_begin, context=context))
            domain = [('mass_mailing_id', '=', mailing.id), ('replied', '>=', date_begin_str), ('replied', '<=', date_end_str)]
            res[mailing.id]['replied_daily'] = json.dumps(self.__get_bar_values(cr, uid, obj, domain, ['replied'], 'replied_count', 'replied:day', date_begin, context=context))
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
            results[mid]['received_ratio'] = 100.0 * results[mid]['delivered'] / (results[mid]['total'] or 1)
            results[mid]['opened_ratio'] = 100.0 * results[mid]['opened'] / (results[mid]['total'] or 1)
            results[mid]['replied_ratio'] = 100.0 * results[mid]['replied'] / (results[mid]['total'] or 1)
        return results

    def _get_mailing_model(self, cr, uid, context=None):
        res = []
        for model_name in self.pool:
            model = self.pool[model_name]
            if hasattr(model, '_mail_mass_mailing') and getattr(model, '_mail_mass_mailing'):
                res.append((model._name, getattr(model, '_mail_mass_mailing')))
        res.append(('mail.mass_mailing.contact', _('Mailing List')))
        return res

    # indirections for inheritance
    _mailing_model = lambda self, *args, **kwargs: self._get_mailing_model(*args, **kwargs)

    _columns = {
        'name': fields.char('Subject', required=True),
        'email_from': fields.char('From', required=True),
        'create_date': fields.datetime('Creation Date'),
        'sent_date': fields.datetime('Sent Date', oldname='date'),
        'body_html': fields.html('Body'),
        'attachment_ids': fields.many2many(
            'ir.attachment', 'mass_mailing_ir_attachments_rel',
            'mass_mailing_id', 'attachment_id', 'Attachments'
        ),
        'mass_mailing_campaign_id': fields.many2one(
            'mail.mass_mailing.campaign', 'Mass Mailing Campaign',
            ondelete='set null',
        ),
        'state': fields.selection(
            [('draft', 'Draft'), ('test', 'Tested'), ('done', 'Sent')],
            string='Status', required=True,
        ),
        'color': fields.related(
            'mass_mailing_campaign_id', 'color',
            type='integer', string='Color Index',
        ),
        # mailing options
        'reply_to_mode': fields.selection(
            [('thread', 'In Document'), ('email', 'Specified Email Address')],
            string='Reply-To Mode', required=True,
        ),
        'reply_to': fields.char('Reply To', help='Preferred Reply-To Address'),
        # recipients
        'mailing_model': fields.selection(_mailing_model, string='Recipients Model', required=True),
        'mailing_domain': fields.char('Domain', oldname='domain'),
        'contact_list_ids': fields.many2many(
            'mail.mass_mailing.list', 'mail_mass_mailing_list_rel',
            string='Mailing Lists',
        ),
        'contact_ab_pc': fields.integer(
            'AB Testing percentage',
            help='Percentage of the contacts that will be mailed. Recipients will be taken randomly.'
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
        # daily ratio
        'opened_daily': fields.function(
            _get_daily_statistics, string='Opened',
            type='char', multi='_get_daily_statistics',
        ),
        'replied_daily': fields.function(
            _get_daily_statistics, string='Replied',
            type='char', multi='_get_daily_statistics',
        )
    }

    def default_get(self, cr, uid, fields, context=None):
        res = super(MassMailing, self).default_get(cr, uid, fields, context=context)
        if 'reply_to_mode' in fields and not 'reply_to_mode' in res and res.get('mailing_model'):
            if res['mailing_model'] in ['res.partner', 'mail.mass_mailing.contact']:
                res['reply_to_mode'] = 'email'
            else:
                res['reply_to_mode'] = 'thread'
        return res

    _defaults = {
        'state': 'draft',
        'email_from': lambda self, cr, uid, ctx=None: self.pool['mail.message']._get_default_from(cr, uid, context=ctx),
        'reply_to': lambda self, cr, uid, ctx=None: self.pool['mail.message']._get_default_from(cr, uid, context=ctx),
        'mailing_model': 'mail.mass_mailing.contact',
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
            'name': _('%s (duplicate)') % mailing.name,
            'sent_date': False,
        })
        return super(MassMailing, self).copy_data(cr, uid, id, default, context=context)

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
        """ Override read_group to always display all states. """
        if groupby and groupby[0] == "state":
            # Default result structure
            # states = self._get_state_list(cr, uid, context=context)
            states = [('draft', 'Draft'), ('test', 'Tested'), ('done', 'Sent')]
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

    def on_change_model_and_list(self, cr, uid, ids, mailing_model, list_ids, context=None):
        value = {}
        if mailing_model == 'mail.mass_mailing.contact':
            mailing_list_ids = set()
            for item in list_ids:
                if isinstance(item, (int, long)):
                    mailing_list_ids.add(item)
                elif len(item) == 3:
                    mailing_list_ids |= set(item[2])
            if mailing_list_ids:
                value['mailing_domain'] = "[('list_id', 'in', %s)]" % list(mailing_list_ids)
            else:
                value['mailing_domain'] = "[('list_id', '=', False)]"
        else:
            value['mailing_domain'] = False
        return {'value': value}

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
        if not len(ids) == 1:
            raise ValueError('One and only one ID allowed for this action')
        mail = self.browse(cr, uid, ids[0], context=context)
        url = '/website_mail/email_designer?model=mail.mass_mailing&res_id=%d&template_model=%s&enable_editor=1' % (ids[0], mail.mailing_model)
        return {
            'name': _('Open with Visual Editor'),
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
        }

    #------------------------------------------------------
    # Email Sending
    #------------------------------------------------------

    def get_recipients(self, cr, uid, mailing, context=None):
        if mailing.mailing_domain:
            domain = eval(mailing.mailing_domain)
            res_ids = self.pool[mailing.mailing_model].search(cr, uid, domain, context=context)
        else:
            res_ids = []
            domain = [('id', 'in', res_ids)]

        # randomly choose a fragment
        if mailing.contact_ab_pc < 100:
            contact_nbr = self.pool[mailing.mailing_model].search(cr, uid, domain, count=True, context=context)
            topick = int(contact_nbr / 100.0 * mailing.contact_ab_pc)
            if mailing.mass_mailing_campaign_id and mailing.mass_mailing_campaign_id.unique_ab_testing:
                already_mailed = self.pool['mail.mass_mailing.campaign'].get_recipients(cr, uid, [mailing.mass_mailing_campaign_id.id], context=context)[mailing.mass_mailing_campaign_id.id]
            else:
                already_mailed = set([])
            remaining = set(res_ids).difference(already_mailed)
            if topick > len(remaining):
                topick = len(remaining)
            res_ids = random.sample(remaining, topick)
        return res_ids

    def send_mail(self, cr, uid, ids, context=None):
        author_id = self.pool['res.users'].browse(cr, uid, uid, context=context).partner_id.id
        for mailing in self.browse(cr, uid, ids, context=context):
            # instantiate an email composer + send emails
            res_ids = self.get_recipients(cr, uid, mailing, context=context)
            if not res_ids:
                raise Warning('Please select recipients.')
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
                'same_thread': mailing.reply_to_mode == 'thread',
            }
            if mailing.reply_to_mode == 'email':
                composer_values['reply_to'] = mailing.reply_to
            composer_id = self.pool['mail.compose.message'].create(cr, uid, composer_values, context=comp_ctx)
            self.pool['mail.compose.message'].send_mail(cr, uid, [composer_id], context=comp_ctx)
            self.write(cr, uid, [mailing.id], {'sent_date': fields.datetime.now(), 'state': 'done'}, context=context)
        return True
