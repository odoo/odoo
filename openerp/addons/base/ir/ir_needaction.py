# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2009-Today OpenERP SA (<http://www.openerp.com>)
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

from osv import osv, fields

class ir_needaction_mixin(osv.Model):
    '''Mixin class for objects using the need action feature.

    Need action feature can be used by objects having to be able to
    signal that an action is required on a particular record. If in
    the business logic an action must be performed by somebody, for
    instance validation by a manager, this mechanism allows to set a
    list of users asked to perform an action.

    Objects using the 'need_action' feature should override the
    ``needaction_domain_get`` method. This methods returns a
    domain to filter records requiring an action for a specific user.

    This class also offers several global services:
    - ``needaction_get_action_count``: as ``needaction_get_record_ids``
    but returns only the number of action, not the ids (performs a
    search with count=True)

    The ``ir_needaction_mixin`` class adds a calculated field
    ``needaction_pending``. This function field allows to state
    whether a given record has a needaction for the current user.
    This is usefull if you want to customize views according to the
    needaction feature. For example, you may want to set records in
    bold in a list view if the current user has an action to perform
    on the record.
    '''

    _name = 'ir.needaction_mixin'
    _description = 'Need Action Mixin'
    _needaction = True

   def get_needaction_pending(self, cr, uid, ids, name, arg, context=None):
       dom = self._needaction_domain_get(cr, uid, context=context)
       result = dict.fromkeys(ids, False)
       ids2 = self.search(cr, uid, [('id','in',ids)+dom], context=context)
       for idna in ids2:
           result[idna] = True
       return result

    def search_needaction_pending(self, cr, uid, field, field_name, criterion, context=None):
        return self._needaction_domain_get(cr, uid, context=context)

    _columns = {
        'needaction_pending': fields.function(
            get_needaction_pending, type='boolean',
            fnct_search=search_needaction_pending,
            string='Need an Action',
            help="Do the current user requires to perform an action."),
    }

    #------------------------------------------------------
    # Addon API
    #------------------------------------------------------

    def _needaction_domain_get(self, cr, uid, context=None):
        """ Returns the domain to filter records that require an action
            :return: domain or False is no need action
        """
        return False

    #------------------------------------------------------
    # "Need action" API
    #------------------------------------------------------

    def _needaction_count(self, cr, uid, domain=[], context=None):
        """Given the current model and a user_id
           get the number of actions it has to perform"""
        dom = self._needaction_domain_get(cr, uid, context=context)
        return self.search(cr, uid, domain+dom, context=context, count=True)

