# Copyright Nova Code (http://www.novacode.nl)
# See LICENSE file for full licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

from ..models.formio_builder import STATE_CURRENT


class FormioCustomerPortal(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super(FormioCustomerPortal, self)._prepare_portal_layout_values()
        domain = [('user_id', '=', request.env.user.id), ('builder_id.portal', '=', True)]
        values['form_count'] = request.env['formio.form'].search_count(domain)
        return values

    def _formio_form_prepare_portal_layout_values(self, **kwargs):
        values = super(FormioCustomerPortal, self)._prepare_portal_layout_values()

        # TODO create model (class)method for this?
        domain = [
            ('portal', '=', True),
            ('formio_res_model_id', '=', False),
            ('state', '=', STATE_CURRENT)
        ]
        # TODO order by sequence?
        order = 'name ASC'
        builders_create_form = request.env['formio.builder'].search(domain, order=order)
        values.update({
            'builders_create_form': builders_create_form,
            'page_name': 'formio',
            'default_url': '/my/formio'
        })

        # Forms
        res_model = kwargs.get('res_model')
        res_id = kwargs.get('res_id')
        if res_model and res_id:
            domain = [
                ('res_model', '=', res_model),
                ('res_id', '=', res_id),
                ('user_id', '=', request.env.user.id),
                ('builder_id.portal', '=', True)
            ]
            forms = request.env['formio.form'].search(domain)
            if forms:
                values['res_model'] = res_model
                values['res_id'] = res_id
                values['res_name'] = forms[0].res_id
                values['form_count'] = len(forms)
        else:
            domain = [('user_id', '=', request.env.user.id), ('builder_id.portal', '=', True)]
            values['form_count'] = request.env['formio.form'].search_count(domain)
        return values

    def _formio_form_get_page_view_values(self, form, **kwargs):
        values = {
            'form': form,
            'page_name': 'formio',
        }
        return self._get_page_view_values(form, False, values, 'my_formio', False, **kwargs)

    def _get_form(self, uuid, mode):
        return request.env['formio.form'].get_form(uuid, mode)

    def _redirect_url(self, **kwargs):
        res_model = kwargs.get('res_model')
        res_id = kwargs.get('res_id')
        if res_model and res_id:
            return '/my/formio?res_model=%s&res_id=%s' % (res_model, res_id)
        else:
            return '/my/formio'

    @http.route(['/my/formio'], type='http', auth="user", website=True)
    def portal_forms(self, sortby=None, search=None, search_in='content',  **kwargs):
        domain = [
            ('user_id', '=', request.env.user.id),
            ('portal_share', '=', True)
        ]
        res_model = kwargs.get('res_model')
        res_id = kwargs.get('res_id')
        if res_model and res_id:
            domain.append(('res_model', '=', res_model))
            domain.append(('res_id', '=', res_id))
        
        order = 'create_date DESC'
        forms = request.env['formio.form'].search(domain, order=order)

        values = self._formio_form_prepare_portal_layout_values(**kwargs)
        values['forms'] = forms
        return request.render("formio.portal_my_formio", values)

    @http.route('/my/formio/form/<string:uuid>', type='http', auth='user', website=True)
    def portal_form(self, uuid, **kwargs):
        form = self._get_form(uuid, 'read')
        if not form:
            # TODO website page with message?
            return request.redirect("/")

        values = self._formio_form_get_page_view_values(form, **kwargs)
        return request.render("formio.portal_my_formio_edit", values)

    @http.route(['/my/formio/form/create/<string:name>'], type='http', auth="user", method=['GET'], website=True)
    def portal_create_form(self, name):
        builder = request.env['formio.builder'].search([('name', '=', name), ('portal', '=', True)], limit=1)
        if not builder:
            redirect_url = self._redirect_url()
            # TODO website page with message?
            return request.redirect(redirect_url)
        vals = {
            'builder_id': builder.id,
            'title': builder.title,
            'user_id': request.env.user.id,
            'partner_id': request.env.user.partner_id.id
        }
        form = request.env['formio.form'].create(vals)
        url = '/my/formio/form/{uuid}'.format(uuid=form.uuid)
        return request.redirect(url)

    @http.route(['/my/formio/form/<string:uuid>/delete'], type='http', auth="user", method=['GET'], website=True)
    def portal_delete_form(self, uuid, **kwargs):
        """ Unlink form. Access rules apply on the unlink method """

        form = request.env['formio.form'].get_form(uuid, 'unlink')
        redirect_url = self._redirect_url(**kwargs)
        if not form:
            # TODO call method (website_formio page) with message?
            return request.redirect(redirect_url)
        form.unlink()
        # TODO call method (website_formio page) with message?

        return request.redirect(redirect_url)

    @http.route(['/my/formio/form/<string:uuid>/cancel'], type='http', auth="user", method=['GET'], website=True)
    def portal_cancel_form(self, uuid, **kwargs):
        """ Cancel form. Access rules apply on the write method """

        form = request.env['formio.form'].get_form(uuid, 'write')
        redirect_url = self._redirect_url(**kwargs)
        if not form:
            # TODO call method (website_formio page) with message?
            return request.redirect(redirect_url)
        form.action_cancel()
        # TODO call method (website_formio page) with message?
        return request.redirect(redirect_url)

    @http.route(['/my/formio/form/<string:uuid>/copy'], type='http', auth="user", method=['GET'], website=True)
    def portal_copy_form(self, uuid, **kwargs):
        form = request.env['formio.form'].get_form(uuid, 'read')
        redirect_url = self._redirect_url(**kwargs)
        if not form:
            # TODO call method (website_formio page) with message?
            return request.redirect(redirect_url)
        form.action_copy()
        # TODO call method (website_formio page) with message?

        return request.redirect(redirect_url)