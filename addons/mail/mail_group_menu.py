# -*- coding: utf-8 -*-

from openerp import api, fields, models


class IrUiMenu(models.Model):
    """ Override of ir.ui.menu class. When adding mail_thread module, each
        new mail.group will create a menu entry. This overrides checks that
        the current user is in the mail.group followers. If not, the menu
        entry is taken off the list of menu ids. This way the user will see
        menu entries for the mail.group he is following.
    """
    _inherit = 'ir.ui.menu'

    mail_group_id = fields.Many2one('mail.group', 'Mail Group')

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        """ Remove mail.group menu entries when the user is not a follower."""
        ids = super(IrUiMenu, self).search(cr, uid, args, offset=offset,
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
