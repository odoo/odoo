# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import Controller, route, request


class View(Controller):

    @route('/web/view/edit_custom', type='json', auth="user")
    def edit_custom(self, custom_id, arch):
        """
        Edit a custom view

        :param int custom_id: the id of the edited custom view
        :param str arch: the edited arch of the custom view
        :returns: dict with acknowledged operation (result set to True)
        """
        custom_view = request.env['ir.ui.view.custom'].browse(custom_id)
        custom_view.write({'arch': arch})
        return {'result': True}
