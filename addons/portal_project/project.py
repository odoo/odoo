# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv
from openerp.tools.translate import _

class portal_project(osv.Model):
    """ Update of mail_mail class, to add the signin URL to notifications. """
    _inherit = 'project.project'

    def _get_visibility_selection(self, cr, uid, context=None):
        """ Override to add portal option. """
        selection = super(portal_project, self)._get_visibility_selection(cr, uid, context=context)
        idx = [item[0] for item in selection].index('public')
        selection.insert((idx + 1), ('portal', _('Customer related project: visible through portal')))
        return selection
        # return [('public', 'All Users'),
        #         ('portal', 'Portal Users and Employees'),
        #         ('employees', 'Employees Only'),
        #         ('followers', 'Followers Only')]
