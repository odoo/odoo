# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv
from openerp.tools.translate import _


class base_stage(object):
    """ Base utility mixin class for objects willing to manage their stages.
        Object that inherit from this class should inherit from mailgate.thread
        to have access to the mail gateway, as well as Chatter. Objects
        subclassing this class should define the following colums:
        - ``date_open`` (datetime field)
        - ``date_closed`` (datetime field)
        - ``user_id`` (many2one to res.users)
        - ``partner_id`` (many2one to res.partner)
        - ``stage_id`` (many2one to a stage definition model)
        - ``state`` (selection field, related to the stage_id.state)
    """

    def _get_default_partner(self, cr, uid, context=None):
        """ Gives id of partner for current user
            :param context: if portal not in context returns False
        """
        if context is None:
            context = {}
        if context.get('portal'):
            user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
            return user.partner_id.id
        return False

    def _get_default_email(self, cr, uid, context=None):
        """ Gives default email address for current user
            :param context: if portal not in context returns False
        """
        if context is None:
            context = {}
        if context.get('portal'):
            user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
            return user.email
        return False

    def _get_default_user(self, cr, uid, context=None):
        """ Gives current user id
            :param context: if portal not in context returns False
        """
        if context is None:
            context = {}
        if not context or context.get('portal'):
            return False
        return uid

    def onchange_partner_address_id(self, cr, uid, ids, address_id, context=None):
        """ This function returns value of partner email based on Partner Address
            :param address_id: partner_id related to the correct address
        """
        if context is None:
            context = {}
        data = {'value': {'email_from': False, 'phone': False}}
        if address_id:
            address = self.pool.get('res.partner').browse(cr, uid, address_id, context=context)
            data['value'] = {'partner_name': address and address.name or False,
                             'email_from': address and address.email or False,
                             'phone':  address and address.phone or False,
                             'mobile': address and address.mobile or False,
                             'fax': address and address.fax or False,
                             'street': address and address.street or False,
                             'street2': address and address.street2 or False,
                             'city': address and address.city or False,
                             'state_id': address.state_id and address.state_id.id or False,
                             'zip': address and address.zip or False,
                             'country_id': address.country_id and address.country_id.id or False,
                             }
        model_fields = self.fields_get(cr, uid, context=context)
        for key in data['value'].keys():
            if key not in model_fields:
                del data['value'][key]
        return data

    def onchange_partner_id(self, cr, uid, ids, partner_id, email=False, context=None):
        """ This function returns value of partner address based on partner """
        data = {}
        if partner_id:
            address = self.pool.get('res.partner').address_get(cr, uid, [partner_id], ['contact'], context=context)
            data.update(self.onchange_partner_address_id(cr, uid, ids, address['contact'], context=context)['value'])
        return {'value': data}

    def _get_default_section_id(self, cr, uid, context=None):
        """ Gives default section """
        return False

    def _get_default_stage_id(self, cr, uid, context=None):
        """ Gives default stage_id """
        section_id = self._get_default_section_id(cr, uid, context=context)
        return self.stage_find(cr, uid, [], section_id, [('sequence', '=', '1')], context=context)

    def stage_find(self, cr, uid, cases, section_id, domain=[], order='sequence', context=None):
        """ Find stage, with a given (optional) domain on the search,
            ordered by the order parameter. If several stages match the
            search criterions, the first one will be returned, according
            to the requested search order.
            This method is meant to be overriden by subclasses. That way
            specific behaviors can be achieved for every class inheriting
            from base_stage.

            :param cases: browse_record of cases
            :param section_id: section limitating the search, given for
                               a generic search (for example default search).
                               A section models concepts such as Sales team
                               (for CRM), ou departments (for HR).
            :param domain: a domain on the search of stages
            :param order: order of the search
        """
        return False

    def stage_set(self, cr, uid, ids, stage_id, context=None):
        """ Set the new stage. This methods is the right method to call
            when changing states. It also checks whether an onchange is
            defined, and execute it.
        """
        value = {}
        if hasattr(self, 'onchange_stage_id'):
            value = self.onchange_stage_id(cr, uid, ids, stage_id, context=context)['value']
        value['stage_id'] = stage_id
        return self.write(cr, uid, ids, value, context=context)

    def stage_change(self, cr, uid, ids, op, order, context=None):
        """ Change the stage and take the next one, based on a condition
            writen for the 'sequence' field and an operator. This methods
            checks whether the case has a current stage, and takes its
            sequence. Otherwise, a default 0 sequence is chosen and this
            method will therefore choose the first available stage.
            For example if op is '>' and current stage has a sequence of
            10, this will call stage_find, with [('sequence', '>', '10')].
        """
        for case in self.browse(cr, uid, ids, context=context):
            seq = 0
            if case.stage_id:
                seq = case.stage_id.sequence or 0
            next_stage_id = self.stage_find(cr, uid, [case], None, [('sequence', op, seq)], order, context=context)
            if next_stage_id:
                return self.stage_set(cr, uid, [case.id], next_stage_id, context=context)
        return False

    def stage_next(self, cr, uid, ids, context=None):
        """ This function computes next stage for case from its current stage
            using available stage for that case type
        """
        return self.stage_change(cr, uid, ids, '>', 'sequence', context)

    def stage_previous(self, cr, uid, ids, context=None):
        """ This function computes previous stage for case from its current
            stage using available stage for that case type
        """
        return self.stage_change(cr, uid, ids, '<', 'sequence desc', context)

    def copy(self, cr, uid, id, default=None, context=None):
        """ Overrides orm copy method to avoid copying messages,
            as well as date_closed and date_open columns if they
            exist."""
        if default is None:
            default = {}

        if hasattr(self, '_columns'):
            if self._columns.get('date_closed'):
                default.update({'date_closed': False})
            if self._columns.get('date_open'):
                default.update({'date_open': False})
        return super(base_stage, self).copy(cr, uid, id, default, context=context)

    def case_escalate(self, cr, uid, ids, context=None):
        """ Escalates case to parent level """
        for case in self.browse(cr, uid, ids, context=context):
            data = {'active': True}
            if case.section_id.parent_id:
                data['section_id'] = case.section_id.parent_id.id
                if case.section_id.parent_id.change_responsible:
                    if case.section_id.parent_id.user_id:
                        data['user_id'] = case.section_id.parent_id.user_id.id
            else:
                raise osv.except_osv(_('Error!'), _("You are already at the top level of your sales-team category.\nTherefore you cannot escalate furthermore."))
            self.write(cr, uid, [case.id], data, context=context)
        return True
