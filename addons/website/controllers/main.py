# -*- coding: utf-8 -*-

from jinja2 import Template # WIP !

import openerp
from openerp.addons.web import http
from openerp.addons.web.controllers.main import manifest_list
from openerp.addons.web.http import request

def get_html_head():
    head = ['<script type="text/javascript" src="%s"></script>' % i for i in manifest_list('js', db=request.db)]
    head += ['<link rel="stylesheet" href="%s">' % i for i in manifest_list('css', db=request.db)]
    head += ['<script type="text/javascript" src="/website/static/src/js/website_editor.js"></script>']
    return "\n        ".join(head)

# WIIIP !!
module_template = Template("""
    {%- for module in modules %}
        <a href='#' title='{{ module.shortdesc }}' class='oe_app ab_app_descr'>
            <div class='ab_app_descr'>
                <div class='oe_app_icon'>
                    <img src="data:image/png;base64,{{ module.icon_image }}" onerror="this.src = '/base/static/src/img/icon.png'">
                </div>
            </div>
            <div
                class='oe_app_name editable'
                data-model='ir.module.module'
                data-id='{{ module.id }}'
                data-field='shortdesc'
            >{{ module.shortdesc }}</div>
            <div
                class='oe_app_descr editable'
                data-model='ir.module.module'
                data-id='{{ module.id }}'
                data-field='summary'
            >{{ module.summary }}</div>
        </a>
    {%- endfor %}
""")


class Website(openerp.addons.web.controllers.main.Home):

    @http.route('/', type='http', auth="db")
    def index(self, **kw):
        editable = bool(request.session._uid)
        try:
            request.session.check_security()
        except http.SessionExpiredException:
            editable = False
        # WIIIIIIIP !!!
        html = open(openerp.addons.get_module_resource('website', 'views', 'homepage.html'), 'rb').read().decode('utf8')
        modules = request.registry.get("ir.module.module").search_read(request.cr, openerp.SUPERUSER_ID, fields=['id', 'shortdesc', 'summary', 'icon_image'], limit=50)
        modules_html = module_template.render(modules=modules)
        html = html.replace(u'<!--modules-->', modules_html)
        if editable:
            html = html.replace('<!--editable-->', get_html_head())
        return html

    @http.route('/admin', type='http', auth="none")
    def admin(self, *args, **kw):
        return super(Website, self).index(*args, **kw)


# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
