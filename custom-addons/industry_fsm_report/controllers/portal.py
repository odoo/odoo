# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import binascii

from odoo import _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request, route
from odoo.addons.industry_fsm.controllers.portal import CustomerPortal


class CustomerFsmPortal(CustomerPortal):

    def _get_worksheet_data(self, task_sudo):
        data = super()._get_worksheet_data(task_sudo)
        worksheet_map = {}
        if task_sudo.worksheet_template_id:
            x_model = task_sudo.worksheet_template_id.model_id.model
            worksheet = request.env[x_model].sudo().search([('x_project_task_id', '=', task_sudo.id)], limit=1, order="create_date DESC")  # take the last one
            worksheet_map[task_sudo.id] = worksheet
        data.update({'worksheet_map': worksheet_map})
        return data

    def _task_get_page_view_values(self, task, access_token, **kwargs):
        data = super()._task_get_page_view_values(task, access_token, **kwargs)
        worksheet_map = self._get_worksheet_data(task)
        data.update(worksheet_map)
        return data

    @route(['/my/task/<int:task_id>/worksheet',
            '/my/task/<int:task_id>/worksheet/<string:source>',
            '/my/task/<int:task_id>/worksheet/sign/<string:source>'], type='http', auth="public")
    def portal_worksheet_outdated(self, **kwargs):
        return request.redirect(request.httprequest.path.replace('/my/task/', '/my/tasks/'))

    @route(['/my/tasks/<int:task_id>/worksheet/sign/<string:source>'], type='json', auth="public", website=True)
    def portal_worksheet_sign(self, task_id, access_token=None, source=False, name=None, signature=None):
        # get from query string if not on json param
        access_token = access_token or request.httprequest.args.get('access_token')
        try:
            task_sudo = self._document_check_access('project.task', task_id, access_token=access_token)
        except (AccessError, MissingError):
            return {'error': _('Invalid Task.')}

        if not task_sudo.has_to_be_signed():
            return {'error': _('The worksheet is not in a state requiring customer signature.')}
        if not signature:
            return {'error': _('Signature is missing.')}

        try:
            task_sudo.write({
                'worksheet_signature': signature,
                'worksheet_signed_by': name,
            })
        except (TypeError, binascii.Error):
            return {'error': _('Invalid signature data.')}

        pdf = request.env['ir.actions.report'].sudo()._render_qweb_pdf('industry_fsm_report.task_custom_report', [task_sudo.id])[0]
        task_sudo.message_post(body=_('The worksheet has been signed'), attachments=[('%s.pdf' % task_sudo.name, pdf)])
        return {
            'force_refresh': True,
            'redirect_url': task_sudo.get_portal_url(query_string=f'&source={source}'),
        }

    def _show_task_report(self, task_sudo, report_type, download):
        if not task_sudo.is_fsm:
            return super()._show_task_report(task_sudo, report_type, download)
        return self._show_report(model=task_sudo, report_type=report_type, report_ref='industry_fsm_report.task_custom_report', download=download)
