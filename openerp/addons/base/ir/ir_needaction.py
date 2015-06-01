# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
