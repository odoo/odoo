# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route

from odoo.addons.html_editor.controllers.main import HTML_Editor


class WebsiteEventHtmlEditor(HTML_Editor):

    @route()
    def modify_image(self, attachment, res_model=None, res_id=None, **kwargs):
        # Images modified in an event page (replaced, cropped, filtered, ...) are saved as copies
        # linked to views, which restricted editors cannot write on.
        if (
            res_model == 'ir.ui.view' and res_id
            and request.env['ir.ui.view'].browse(int(res_id))._can_be_edited_by_event_editor()
        ):
            # The original image is still read with the rights of the user
            attachment.check_access('read')
            request.update_env(su=True)
        return super().modify_image(attachment, res_model=res_model, res_id=res_id, **kwargs)
