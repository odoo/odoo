# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Board(models.AbstractModel):
    _name = 'board.board'
    _description = "Board"
    _auto = False

    # This is necessary for when the web client opens a dashboard. Technically
    # speaking, the dashboard is a form view, and opening it makes the client
    # initialize a dummy record by invoking onchange(). And the latter requires
    # an 'id' field to work properly...
    id = fields.Id()

    @api.model_create_multi
    def create(self, vals_list):
        return self

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        """
        Overrides orm field_view_get.
        @return: Dictionary of Fields, arch and toolbar.
        """

        res = super().get_view(view_id, view_type, **options)

        custom_view = self.env['ir.ui.view.custom'].search([('user_id', '=', self.env.uid), ('ref_id', '=', view_id)], limit=1)
        if custom_view:
            res.update({'custom_view_id': custom_view.id,
                        'arch': custom_view.arch})
        res['arch'] = self._arch_preprocessing(res['arch'])
        return res

    @api.model
    def get_views(self, views, options=None):
        res = super().get_views(views, options)
        for view in res['views'].values():
            view['toolbar'] = {'print': [], 'action': [], 'relate': []}
        return res

    @api.model
    def _arch_preprocessing(self, arch):
        from lxml import etree

        def remove_unauthorized_children(node):
            for child in node.iterchildren():
                if child.tag == 'action' and child.get('invisible'):
                    node.remove(child)
                else:
                    remove_unauthorized_children(child)
            return node

        archnode = etree.fromstring(arch)
        # add the js_class 'board' on the fly to force the webclient to
        # instantiate a BoardView instead of FormView
        archnode.set('js_class', 'board')
        return etree.tostring(remove_unauthorized_children(archnode), pretty_print=True, encoding='unicode')
