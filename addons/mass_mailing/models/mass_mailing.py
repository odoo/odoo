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


class MassMailingList(osv.Model):
    """Model of a contact list. """
    _name = 'mail.mass_mailing.list'
    _order = 'name'
    _description = 'Mailing List'
    _columns = {
        'name': fields.char('Mailing List', required=True),
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
    _columns = {
        'name': fields.char('Name', required=True),
        'stage_id': fields.many2one('mail.mass_mailing.stage', 'Stage', required=True),
        'user_id': fields.many2one(
            'res.users', 'Responsible',
            required=True,
        ),
        'category_ids': fields.many2many('mail.mass_mailing.category', 'mail_mass_amiling_category_rel', 
            'category_id', 'campaign_id', string='Categories'),
        'mass_mailing_ids': fields.one2many(
            'mail.mass_mailing', 'mass_mailing_campaign_id',
            'Mass Mailings',
        ),
        'color': fields.integer('Color Index'),
    }

    def _get_default_stage_id(self, cr, uid, context=None):
        stage_ids = self.pool['mail.mass_mailing.stage'].search(cr, uid, [], limit=1, context=context)
        return stage_ids and stage_ids[0] or False

    _defaults = {
        'user_id': lambda self, cr, uid, ctx=None: uid,
        'stage_id': lambda self, *args: self._get_default_stage_id(*args),
    }


class MassMailing(osv.Model):
    """ MassMailing models a wave of emails for a mass mailign campaign.
    A mass mailing is an occurence of sending emails. """
    _name = 'mail.mass_mailing'
    _description = 'Mass Mailing'
    _order = 'id DESC'

    def _get_private_models(self, context=None):
        return ['res.partner', 'mail.mass_mailing.contact']

    def _get_auto_reply_to_available(self, cr, uid, ids, name, arg, context=None):
        res = dict.fromkeys(ids, False)
        for mailing in self.browse(cr, uid, ids, context=context):
            res[mailing.id] = mailing.mailing_model not in self._get_private_models(context=context)
        return res

    def _get_mailing_model(self, cr, uid, context=None):
        return [
            ('res.partner', _('Customers')),
            ('mail.mass_mailing.contact', _('Mailing List'))
        ]

    _columns = {
        'name': fields.char('Subject', required=True),
        'email_from': fields.char('From', required=True),
        'date': fields.datetime('Date'),
        'body_html': fields.html('Body'),

        'mass_mailing_campaign_id': fields.many2one(
            'mail.mass_mailing.campaign', 'Mass Mailing Campaign',
            ondelete='set null',
        ),
        'state': fields.selection(
            [('draft', 'Draft'), ('test', 'Tested'), ('done', 'Sent')], string='Status', required=True,
        ),
        'color': fields.related(
            'mass_mailing_campaign_id', 'color',
            type='integer', string='Color Index',
        ),

        # mailing options
        # TODO: simplify these 4 fields
        'reply_in_thread': fields.boolean('Reply in thread'),
        'reply_specified': fields.boolean('Specific Reply-To'),
        'auto_reply_to_available': fields.function(
            _get_auto_reply_to_available,
            type='boolean', string='Reply in thread available'
        ),
        'reply_to': fields.char('Reply To'),

        # Target Emails
        'mailing_model': fields.selection(_get_mailing_model, string='Recipients Model', required=True),
        'mailing_domain': fields.char('Domain'),
        'contact_list_ids': fields.many2many(
            'mail.mass_mailing.list', 'mail_mass_mailing_list_rel',
            string='Mailing Lists',
        ),
        'contact_ab_pc': fields.integer(
            'AB Testing percentage',
            help='Percentage of the contacts that will be mailed. Recipients will be taken randomly.'
        ),
    }

    _defaults = {
        'state': 'draft',
        'date': fields.datetime.now,
        'email_from': lambda self, cr, uid, ctx=None: self.pool['mail.message']._get_default_from(cr, uid, context=ctx),
        'mailing_model': 'mail.mass_mailing.contact',
        'contact_ab_pc': 100,
    }

    #------------------------------------------------------
    # Technical stuff
    #------------------------------------------------------

    def copy_data(self, cr, uid, id, default=None, context=None):
        default = default or {}
        mailing = self.browse(cr, uid, id, context=context)
        default.update({
            'state': 'draft',
            'statistics_ids': [],
            'name': _('%s (duplicate)') % mailing.name,
        })
        return super(MassMailing, self).copy_data(cr, uid, id, default, context=context)

    #------------------------------------------------------
    # Views & Actions
    #------------------------------------------------------
    def on_change_model(self, cr, uid, ids, mailing_model, list_ids, context=None):
        value = {}
        if mailing_model=='mail.mass_mailing.contact':
            if list_ids and list_ids[0][0]==6 and list_ids[0][2]:
                value['mailing_domain'] = "[('list_id', 'in', ["+','.join(map(str, list_ids[0][2]))+"])]"
            else:
                value['mailing_domain'] = "[('list_id', '=', False)]"
            value['contact_nbr'] = self.pool[mailing_model].search(
                cr, uid, eval(value['mailing_domain']), count=True, context=context
            )
        else:
            value['mailing_domain'] = False
            value['contact_nbr'] = 0
        return {'value': value}

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

    def action_domain_select(self, cr, uid, ids, context=None):
        mailing = self.browse(cr, uid, ids[0], context=context)
        ctx = dict(
            context,
            search_default_not_opt_out=True,
            view_manager_highlight=[action_id],         # To Change
            default_mass_mailing_id=ids[0],
            default_model=mailing.mailing_model
        )
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
        assert len(ids)==1, "One and only one ID allowed for this action"
        mail = self.browse(cr, uid, ids[0], context=context)
        url = '/website_mail/email_designer?model=mail.mass_mailing&res_id=%d&field_body=body_html&field_from=email_form&field_subject=name&template_model=%s' % (ids[0], mail.mailing_model)
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


