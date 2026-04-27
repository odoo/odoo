# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from lxml import html

from odoo import http
from odoo.http import request
import werkzeug.exceptions


class WebsiteStudioController(http.Controller):
    @http.route('/website_studio/create_form', type='json', auth='user')
    def create_website_form(self, res_model):
        """ Create a new website page containing a form for the model.

            :param str res_model: the model technical name
            :return: xml_id of the website page containing the form
            :rtype: string
        """
        model = request.env['ir.model']._get(res_model)
        values = {}
        if not model.website_form_access:
            values['website_form_access'] = True
            if not model.website_form_label:
                values['website_form_label'] = "Create %s" % model.name
        model.write(values)
        template = 'website_studio.default_record_page'
        form_name = model.name
        page_url = '/' + request.env['ir.http']._slugify(form_name, max_length=1024, path=True)
        try:
            # Pages are served as a fallback when Python routing (@route) doesn't
            # match and there is no attachment matching that url. For simplicity and
            # performance, we only check that our new page doesn't collide with an
            # @route controller, because we assume that attachments url won't collide.
            # see website/models/ir_http.py Http::_serve_fallback
            if request.env['ir.http']._match(page_url):
                form_name = form_name + ' Form'
        except werkzeug.exceptions.NotFound:
            pass
        new_page = request.env['website'].new_page(
            name=form_name,
            add_menu=True,
            template=template,
            ispage=True,
            namespace='website',
        )
        view = request.env['ir.ui.view'].browse(new_page['view_id'])
        view.arch = self._post_process_arch(view.arch, model)
        return new_page['url']

    @http.route('/website_studio/get_forms', type='json', auth='user')
    def get_website_form(self, res_model):
        """ Search and return all the website views containing forms linked to the model.

            :param str res_model: the model technical name
            :return: dict of the views containing a form linked to the model
            :rtype: dict
        """
        views = request.env['ir.ui.view'].search([('type', '=', 'qweb')])
        website_forms = views.filtered(lambda v: self._is_editable_form(v, res_model))
        return request.env['website.page'].search_read(
            [('view_id', 'in', website_forms.ids)],
            ['url', 'name']
        )

    def _is_editable_form(self, view, res_model):
        """ Check if the view contains an editable form.
            Some forms are static and shouldn't be edited by the studio users,
            they are tagged with the 'data-editable-form' set to 'false'.

            :param record view: ir.ui.view record being tested
            :param str res_model: the model technical name
            :return: true if the form in the view is editable, false if not
            :rtype: boolean
        """
        html_element = html.fromstring(view.arch_base)
        path = '//form[@action="/website/form/"][@data-model_name="%s"]' % res_model
        form_element = html_element.xpath(path)
        if not len(form_element):
            return False
        # The non editable forms have been modified to have the "data-editable-form"
        # attribute set to false. So the editable forms are the one without
        # the attribute or if the attribute is set to true.
        editable_form = 'data-editable-form' not in form_element[0].attrib or\
            form_element[0].attrib['data-editable-form'] == "true"
        return editable_form

    def _post_process_arch(self, arch, res_model):
        """ Modify the default arch to set the linked model and insert
            an input for the name (or x_name) in the form
            if the field exists in the model.

            :param str arch: view arch containing the form
            :param record res_model: the model to link to the form
            :return: the modified arch
            :rtype: str
        """
        model = request.env['%s' % res_model.model]
        if model.fields_get(['name']):
            arch = request.env['ir.ui.view'].search([('key', '=', 'website_studio.default_form_field_name')]).arch
        elif model.fields_get(['x_name']):
            request.env['ir.model.fields'].formbuilder_whitelist(res_model.model, ['x_name'])
            arch = request.env['ir.ui.view'].search([('key', '=', 'website_studio.default_form_field_name')]).arch
            arch = re.sub(r'for="name"', 'for="x_name"', arch)
            arch = re.sub(r'name="name"', 'name="x_name"', arch)
        # Add the correct model to the website_form snippet
        arch = re.sub(r'data-model_name=""', 'data-model_name="%s"' % res_model.model, arch)
        return arch

    @http.route("/website_studio/get_website_pages", type="json", auth="user")
    def get_website_pages(self, res_model=None):
        pages = request.env["website.controller.page"].search_read(
            [("model", "=", res_model)],
            ["website_id", "name", "name_slugified"]
        )
        return {
            "pages": pages,
            "websites": request.env["website"].search_read([], ["display_name"]),
        }
