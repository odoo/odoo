# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.portal.controllers import portal



class CustomerPortal(portal.CustomerPortal):

    def _get_worksheet_data(self, task_sudo):
        # TO BE OVERRIDDEN
        return {}

    def _task_get_page_view_values(self, task, access_token, **kwargs):
        values = super()._task_get_page_view_values(task, access_token, **kwargs)
        values['source'] = kwargs.get('source')
        return values
