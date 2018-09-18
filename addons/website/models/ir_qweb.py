# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
from collections import OrderedDict

from odoo import models
from odoo.http import request
from odoo.addons.base.models.assetsbundle import AssetsBundle
from odoo.tools import html_escape as escape

re_background_image = re.compile(r"(background-image\s*:\s*url\(\s*['\"]?\s*)([^)'\"]+)")


class AssetsBundleMultiWebsite(AssetsBundle):
    def _get_asset_url_values(self, id, unique, extra, name, page, type):
        website_id = self.env.context.get('website_id')
        website_id_path = website_id and ('%s/' % website_id) or ''
        extra = website_id_path + extra
        res = super(AssetsBundleMultiWebsite, self)._get_asset_url_values(id, unique, extra, name, page, type)
        return res


class QWeb(models.AbstractModel):
    """ QWeb object for rendering stuff in the website context """

    _inherit = 'ir.qweb'

    URL_ATTRS = {
        'form':   'action',
        'a':      'href',
        'link':   'href',
        'script': 'src',
        'img':    'src',
    }

    def get_asset_bundle(self, xmlid, files, remains=None, env=None):
        return AssetsBundleMultiWebsite(xmlid, files, remains=remains, env=env)

    def _compile_directive_module(self, el, options):
        """
            Compile the directive t-module. Its goal is to suggest to the user a module to install.
            This method will add the relevant data-module- fields on the current element.
            The actual display will be done in JavaScript.
            Expected value: the technical name of the module to install.

            - If the module does not exist (developer error): raise
            - If the module is installed: show the element normally
            - If the module is not installed: add the module data to the element
        """
        module_name = el.attrib.pop('t-module')
        module = self.env['ir.module.module'].sudo().search([('name', '=', module_name)])
        if not module:
            raise Exception("t-module must contain a valid module name instead of: %s" % module_name)

        if module.state != 'installed':
            el.set('data-module-id', str(module.id))
            el.set('data-module-shortdesc', escape(module.shortdesc))
            el.set('data-module-can-install', "1" if self.user_has_groups('base.group_system') else "0")

        return self._compile_directives(el, options)

    def _directives_eval_order(self):
        directives = super(QWeb, self)._directives_eval_order()
        directives.insert(directives.index('call'), 'module')
        return directives

    def _post_processing_att(self, tagName, atts, options):
        if atts.get('data-no-post-process'):
            return atts

        atts = super(QWeb, self)._post_processing_att(tagName, atts, options)

        if options.get('inherit_branding') or options.get('rendering_bundle') or \
           options.get('edit_translations') or options.get('debug') or (request and request.debug):
            return atts

        website = request and getattr(request, 'website', None)
        if not website and options.get('website_id'):
            website = self.env['website'].browse(options['website_id'])

        if not website or not website.cdn_activated:
            return atts

        name = self.URL_ATTRS.get(tagName)
        if name and name in atts:
            atts = OrderedDict(atts)
            atts[name] = website.get_cdn_url(atts[name])
        if isinstance(atts.get('style'), str) and 'background-image' in atts['style']:
            atts = OrderedDict(atts)
            atts['style'] = re_background_image.sub(lambda m: '%s%s' % (m.group(1), website.get_cdn_url(m.group(2))), atts['style'])

        return atts
