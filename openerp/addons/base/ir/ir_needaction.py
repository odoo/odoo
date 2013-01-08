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

from openerp.osv import osv


class ir_needaction_mixin(osv.AbstractModel):
    """Mixin class for objects using the need action feature.

    Need action feature can be used by models that have to be able to
    signal that an action is required on a particular record. If in
    the business logic an action must be performed by somebody, for
    instance validation by a manager, this mechanism allows to set a
    list of users asked to perform an action.

    Models using the 'need_action' feature should override the
    ``_needaction_domain_get`` method. This method returns a
    domain to filter records requiring an action for a specific user.

    This class also offers several global services:
    - ``_needaction_count``: returns the number of actions uid has to perform
    """

    _name = 'ir.needaction_mixin'
    _needaction = True

    #------------------------------------------------------
    # Addons API
    #------------------------------------------------------

    def _needaction_domain_get(self, cr, uid, context=None):
        """ Returns the domain to filter records that require an action
            :return: domain or False is no action
        """
        return False

    #------------------------------------------------------
    # "Need action" API
    #------------------------------------------------------

    def _needaction_count(self, cr, uid, domain=None, context=None):
        """ Get the number of actions uid has to perform. """
        dom = self._needaction_domain_get(cr, uid, context=context)
        if not dom:
            return 0
        res = self.search(cr, uid, (domain or []) + dom, limit=100, order='id DESC', context=context)
        return len(res)
