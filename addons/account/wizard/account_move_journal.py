# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from lxml import etree

from osv import osv, fields
from tools.translate import _
import tools

class account_move_journal(osv.osv_memory):
    _name = "account.move.journal"
    _description = "Move journal"

    _columns = {
       'target_move': fields.selection([('posted', 'All Posted Entries'),
                                        ('all', 'All Entries'),
                                        ], 'Target Moves', required=True),
    }

    _defaults = {
        'target_move': 'all'
    }
    def _get_period(self, cr, uid, context={}):
        """
        Return  default account period value
        """
        account_period_obj = self.pool.get('account.period')
        ids = account_period_obj.find(cr, uid, context=context)
        period_id = False
        if ids:
            period_id = ids[0]
        return period_id

    def _get_journal(self, cr, uid, context=None):
        """
        Return journal based on the journal type
        """

        journal_id = False

        journal_pool = self.pool.get('account.journal')
        if context.get('journal_type', False):
            jids = journal_pool.search(cr, uid, [('type','=', context.get('journal_type'))])
            if not jids:
                raise osv.except_osv(_('Configuration Error !'), _('Can\'t find any account journal of %s type for this company.\n\nYou can create one in the menu: \nConfiguration/Financial Accounting/Accounts/Journals.') % context.get('journal_type'))
            journal_id = jids[0]

        return journal_id

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        """
        Returns views and fields for current model where view will depend on {view_type}.
        @param cr: A database cursor
        @param user: ID of the user currently logged in
        @param view_id: list of fields, which required to read signatures
        @param view_type: defines a view type. it can be one of (form, tree, graph, calender, gantt, search, mdx)
        @param context: context arguments, like lang, time zone
        @param toolbar: contains a list of reports, wizards, and links related to current model

        @return: Returns a dict that contains definition for fields, views, and toolbars
        """
        if context is None:context = {}
        res = super(account_move_journal, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar,submenu=False)

        if context:
            if not view_id:
                return res
    
            period_pool = self.pool.get('account.period')
            journal_pool = self.pool.get('account.journal')
    
            journal_id = self._get_journal(cr, uid, context)
            period_id = self._get_period(cr, uid, context)
    
            journal = False
            if journal_id:
                journal = journal_pool.read(cr, uid, [journal_id], ['name'])[0]['name']
                journal_string = _("Journal: %s") % tools.ustr(journal)
            else:
                journal_string = _("Journal: All")
    
            period = False
            if period_id:
                period = period_pool.browse(cr, uid, [period_id], ['name'])[0]['name']
                period_string = _("Period: %s") % tools.ustr(period)
    
            open_string = _("Open")
            view = """<?xml version="1.0" encoding="utf-8"?>
            <form string="Standard entries" version="7.0">
                <group>
                    <field name="target_move"/>
                </group>
                <label width="300" string="%s"/>
                <newline/>
                <label width="300" string="%s"/>
                <footer>
                    <button string="%s" name="action_open_window" default_focus="1" type="object" class="oe_highlight"/>
                    or
                    <button string="Cancel" class="oe_link" special="cancel"/>
                </footer>
            </form>""" % (journal_string, period_string, open_string)
    
            view = etree.fromstring(view.encode('utf8'))
            xarch, xfields = self._view_look_dom_arch(cr, uid, view, view_id, context=context)
            view = xarch
            res.update({
                'arch': view
            })
        return res

    def action_open_window(self, cr, uid, ids, context=None):
        """
        This function Open action move line window on given period and  Journal/Payment Mode
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: account move journal’s ID or list of IDs
        @return: dictionary of Open action move line window on given period and  Journal/Payment Mode
        """

        period_pool = self.pool.get('account.journal.period')
        data_pool = self.pool.get('ir.model.data')
        journal_pool = self.pool.get('account.journal')
        account_period_obj = self.pool.get('account.period')

        if context is None:
            context = {}

        journal_id = self._get_journal(cr, uid, context)
        period_id = self._get_period(cr, uid, context)
        target_move = self.read(cr, uid, ids, ['target_move'], context=context)[0]['target_move']

        name = _("Journal Items")
        if journal_id:
            ids = period_pool.search(cr, uid, [('journal_id', '=', journal_id), ('period_id', '=', period_id)], context=context)

            if not ids:
                journal = journal_pool.browse(cr, uid, journal_id, context=context)
                period = account_period_obj.browse(cr, uid, period_id, context=context)

                name = journal.name
                state = period.state

                if state == 'done':
                    raise osv.except_osv(_('UserError'), _('This period is already closed !'))

                company = period.company_id.id
                res = {
                    'name': name,
                    'period_id': period_id,
                    'journal_id': journal_id,
                    'company_id': company
                }
                period_pool.create(cr, uid, res,context=context)

            ids = period_pool.search(cr, uid, [('journal_id', '=', journal_id), ('period_id', '=', period_id)], context=context)
            period = period_pool.browse(cr, uid, ids[0], context=context)
            name = (period.journal_id.code or '') + ':' + (period.period_id.code or '')

        result = data_pool.get_object_reference(cr, uid, 'account', 'view_account_move_line_filter')
        res_id = result and result[1] or False
        move = 0
        if target_move == 'posted':
            move = 1
        return {
            'name': name,
            'view_type': 'form',
            'view_mode': 'tree,graph,form',
            'res_model': 'account.move.line',
            'view_id': False,
            'context': "{'search_default_posted': %d, 'search_default_journal_id':%d, 'search_default_period_id':%d}" % (move, journal_id, period_id),
            'type': 'ir.actions.act_window',
            'search_view_id': res_id
        }

account_move_journal()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
