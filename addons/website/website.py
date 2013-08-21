# -*- coding: utf-8 -*-
import simplejson

import openerp
from openerp.osv import osv, orm
from openerp.addons.web import http
from openerp.addons.web.controllers import main
from openerp.addons.web.http import request
import urllib
import math
import traceback

import logging
logger = logging.getLogger(__name__)


def auth_method_public():
    registry = openerp.modules.registry.RegistryManager.get(request.db)
    if not request.session.uid:
        request.uid = registry['website'].get_public_user().id
    else:
        request.uid = request.session.uid
http.auth_methods['public'] = auth_method_public


def urlplus(url, params):
    if not params:
        return url
    url += "?"
    for k,v in params.items():
        url += "%s=%s&" % (k, urllib.quote_plus(str(v)))
    return url


class website(osv.osv):
    _name = "website" # Avoid website.website convention for conciseness (for new api). Got a special authorization from xmo and rco
    _description = "Website"

    public_user = None

    def get_public_user(self):
        if not self.public_user:
            ref = request.registry['ir.model.data'].get_object_reference(request.cr, openerp.SUPERUSER_ID, 'website', 'public_user')
            self.public_user = request.registry[ref[0]].browse(request.cr, openerp.SUPERUSER_ID, ref[1])
        return self.public_user

    def get_rendering_context(self, additional_values=None):
        debug = 'debug' in request.params
        is_logged = True
        try:
            request.session.check_security()
        except: # TODO fme: check correct exception
            is_logged = False
        is_public_user = request.uid == self.get_public_user().id
        values = {
            'debug': debug,
            'is_public_user': is_public_user,
            'editable': is_logged and not is_public_user,
            'request': request,
            'registry': request.registry,
            'cr': request.cr,
            'uid': request.uid,
            'host_url': request.httprequest.host_url,
            'res_company': request.registry['res.company'].browse(request.cr, openerp.SUPERUSER_ID, 1),
            'json': simplejson,
        }
        if additional_values:
            values.update(additional_values)
        return values

    def render(self, template, values={}):
        context = {
            'inherit_branding': values.get('editable', False),
        }
        try:
            return request.registry.get("ir.ui.view").render(request.cr, request.uid, template, values, context=context)
        except (osv.except_osv, orm.except_orm), err:
            logger.error(err)
            values['error'] = err[1]
            return self.render('website.401', values)
        except ValueError:
            logger.error("Website Rendering Error.\n\n%s" % (traceback.format_exc()))
            return self.render('website.404', values)
        except Exception:
            logger.error("Website Rendering Error.\n\n%s" % (traceback.format_exc()))
            if values['editable']:
                values['traceback'] = traceback.format_exc()
                return self.render('website.500', values)
            else:
                return self.render('website.404', values)

    def pager(self, url, total, page=1, step=30, scope=5, url_args=None):
        # Compute Pager
        d = {}
        d["page_count"] = int(math.ceil(float(total) / step))

        page = max(1, min(int(page), d["page_count"]))

        d["offset"] = (page-1) * step
        scope -= 1

        pmin = max(page - int(math.floor(scope/2)), 1)
        pmax = min(pmin + scope, d["page_count"])

        if pmax - pmin < scope:
            pmin = pmax - scope > 0 and pmax - scope or 1

        def get_url(page):
            _url = "%spage/%s/" % (url, page)
            if url_args:
                _url = "%s?%s" % (_url, urllib.urlencode(url_args))
            return _url

        d["page"] = {'url': get_url(page), 'num': page}
        d["page_start"] = {'url': get_url(pmin), 'num': pmin}
        d["page_end"] = {'url': get_url(min(pmax, page+1)), 'num': min(pmax, page+1)}
        d["pages"] = []
        for page in range(pmin, pmax+1):
            d["pages"].append({'url': get_url(page), 'num': page})

        return d

    def list_pages(self, cr, uid, context=None):
        """ Available pages in the website/CMS. This is mostly used for links
        generation and can be overridden by modules setting up new HTML
        controllers for dynamic pages (e.g. blog).

        By default, returns template views marked as pages.

        :returns: a list of mappings with two keys: ``name`` is the displayable
                  name of the resource (page), ``url`` is the absolute URL
                  of the same.
        :rtype: list({name: str, url: str})
        """
        View = self.pool['ir.ui.view']
        views = View.search_read(cr, uid, [['page', '=', True]],
                                 fields=['name'], order='name', context=context)
        xids = View.get_external_id(cr, uid, [view['id'] for view in views], context=context)

        return [
            {'name': view['name'], 'url': '/page/' + xids[view['id']]}
            for view in views
            if xids[view['id']]
        ]


class res_partner(osv.osv):
    _inherit = "res.partner"

    def google_map_img(self, cr, uid, ids, zoom=8, width=298, height=298, context=None):
        partner = self.browse(cr, uid, ids[0], context=context)
        params = {
            'center': '%s, %s %s, %s' % (partner.street, partner.city, partner.zip, partner.country_id and partner.country_id.name_get()[0][1] or ''),
            'size': "%sx%s" % (height, width),
            'zoom': zoom,
            'sensor': 'false',
        }
        return urlplus('http://maps.googleapis.com/maps/api/staticmap' , params)

    def google_map_link(self, cr, uid, ids, zoom=8, context=None):
        partner = self.browse(cr, uid, ids[0], context=context)
        params = {
            'q': '%s, %s %s, %s' % (partner.street, partner.city, partner.zip, partner.country_id and partner.country_id.name_get()[0][1] or ''),
        }
        return urlplus('https://maps.google.be/maps' , params)
