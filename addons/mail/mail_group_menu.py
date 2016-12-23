# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012-today OpenERP SA (<http://www.openerp.com>)
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
from openerp.osv import fields
from openerp import tools, SUPERUSER_ID

class ir_ui_menu(osv.osv):
    """ Override of ir.ui.menu class. When adding mail_thread module, each
        new mail.group will create a menu entry. This overrides checks that
        the current user is in the mail.group followers. If not, the menu
        entry is taken off the list of menu ids. This way the user will see
        menu entries for the mail.group he is following.
    """
    _inherit = 'ir.ui.menu'

    _columns = {
        'mail_group_id': fields.many2one('mail.group', 'Mail Group')
    }

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        """ Remove mail.group menu entries when the user is not a follower."""
        ids = super(ir_ui_menu, self).search(cr, uid, args, offset=offset,
                                             limit=limit, order=order,
                                             context=context, count=False)
        if ids:
            cr.execute("""
                SELECT id FROM ir_ui_menu m
                WHERE m.mail_group_id IS NULL OR EXISTS (
                        SELECT 1 FROM mail_followers
                        WHERE res_model = 'mail.group' AND res_id = m.mail_group_id
                            AND partner_id = (SELECT partner_id FROM res_users WHERE id = %s)
                      ) AND id in %s
            """, (uid, tuple(ids)))
            # Preserve original search order
            visible_ids = set(x[0] for x in cr.fetchall())
            ids = [i for i in ids if i in visible_ids]
        if count:
            return len(ids)
        return ids


class ir_translation(osv.Model):
    _name = "ir.translation"
    _inherit = "ir.translation"

    @tools.ormcache_multi(skiparg=3, multi=6)
    def _get_ids(self, cr, uid, name, tt, lang, ids):
        res = super(ir_translation, self)._get_ids(cr, uid, name, tt, lang, ids)
        if ids and name == 'ir.ui.menu,name' and tt == 'model':
            no_translation_menu_ids = [menu_id for menu_id, translation in res.items() if not translation]
            if no_translation_menu_ids:
                # SUPERUSER_ID is used:
                # - to bypass the security, for greater performances
                # - the list `ids` already contains only the menu ids that the user can access to.
                to_translate_mail_group_menu_ids = self.pool['ir.ui.menu'].search_read(cr, SUPERUSER_ID, [('id', 'in', no_translation_menu_ids), ('mail_group_id', '!=', False)], ['mail_group_id'])
                mail_group_translations = self._get_ids(cr, uid, 'mail.group,name', tt, lang, [menu['mail_group_id'][0] for menu in to_translate_mail_group_menu_ids])
                res.update(dict((menu['id'], mail_group_translations[menu['mail_group_id'][0]]) for menu in to_translate_mail_group_menu_ids))
        return res
