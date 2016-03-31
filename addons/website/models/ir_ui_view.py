# -*- coding: ascii -*-
import copy
import logging

from itertools import groupby
from lxml import etree, html

from openerp import SUPERUSER_ID, api, tools
from openerp.addons.website.models import website
from openerp.http import request
from openerp.osv import osv, fields

_logger = logging.getLogger(__name__)


class view(osv.osv):
    _name = "ir.ui.view"
    _inherit = ["ir.ui.view", "website.seo.metadata"]
    _columns = {
        'page': fields.boolean("Whether this view is a web page template (complete)"),
        'customize_show': fields.boolean("Show As Optional Inherit"),
        'website_id': fields.many2one('website', ondelete='cascade', string="Website"),
    }

    _defaults = {
        'page': False,
        'customize_show': False,
    }

    def unlink(self, cr, uid, ids, context=None):
        res = super(view, self).unlink(cr, uid, ids, context=context)
        self.clear_caches()
        return res

    def _sort_suitability_key(self):
        """
        Key function to sort views by descending suitability
        Suitability of a view is defined as follow:

        * if the view and request website_id are matched
        * then if the view has no set website
        """
        context_website_id = self.env.context.get('website_id', 1)
        website_id = self.website_id.id or 0
        different_website = context_website_id != website_id

        return (different_website, website_id)

    def filter_duplicate(self):
        """
        Filter current recordset only keeping the most suitable view per distinct key
        """
        filtered = self.browse([])
        for _, group in groupby(self, key=lambda r:r.key):
            filtered += sorted(group, key=lambda r:r._sort_suitability_key())[0]
        return filtered

    def _view_obj(self, cr, uid, view_id, context=None):
        if isinstance(view_id, basestring):
            if 'website_id' in (context or {}):
                domain = [('key', '=', view_id), '|', ('website_id', '=', False), ('website_id', '=', context.get('website_id'))]
                rec_id = self.search(cr, uid, domain, order='website_id', context=context)
            else:
                rec_id = self.search(cr, uid, [('key', '=', view_id)], context=context)
            if rec_id:
                return self.browse(cr, uid, rec_id, context=context).filter_duplicate()
            else:
                return self.pool['ir.model.data'].xmlid_to_object(
                    cr, uid, view_id, raise_if_not_found=True, context=context)
        elif isinstance(view_id, (int, long)):
            return self.browse(cr, uid, view_id, context=context)

        # assume it's already a view object (WTF?)
        return view_id

    # Returns all views (called and inherited) related to a view
    # Used by translation mechanism, SEO and optional templates
    def _views_get(self, cr, uid, view_id, options=True, bundles=False, context=None, root=True):
        """ For a given view ``view_id``, should return:

        * the view itself
        * all views inheriting from it, enabled or not
          - but not the optional children of a non-enabled child
        * all views called from it (via t-call)
        """

        try:
            view = self._view_obj(cr, uid, view_id, context=context)
        except ValueError:
            _logger.warning("Could not find view object with view_id '%s'" % (view_id))
            # Shall we log that ? Yes, you should !
            return []

        while root and view.inherit_id:
            view = view.inherit_id

        result = [view]

        node = etree.fromstring(view.arch)
        xpath = "//t[@t-call]"
        if bundles:
            xpath += "| //t[@t-call-assets]"
        for child in node.xpath(xpath):
            try:
                called_view = self._view_obj(cr, uid, child.get('t-call', child.get('t-call-assets')), context=context)
            except ValueError:
                continue
            if called_view not in result:
                result += self._views_get(cr, uid, called_view, options=options, bundles=bundles, context=context)

        extensions = view.inherit_children_ids
        if not options:
            # only active children
            extensions = (v for v in view.inherit_children_ids if v.active)

        # Keep options in a deterministic order regardless of their applicability
        for extension in sorted(extensions, key=lambda v: v.id):
            for r in self._views_get(
                    cr, uid, extension,
                    # only return optional grandchildren if this child is enabled
                    options=extension.active,
                    context=context, root=False):
                if r not in result:
                    result.append(r)
        return result

    @tools.ormcache_context('uid', 'xml_id', keys=('website_id',))
    def get_view_id(self, cr, uid, xml_id, context=None):
        if context and 'website_id' in context and not isinstance(xml_id, (int, long)):
            domain = [('key', '=', xml_id), '|', ('website_id', '=', context['website_id']), ('website_id', '=', False)]
            [view_id] = self.search(cr, uid, domain, order='website_id', limit=1, context=context) or [None]
            if not view_id:
                _logger.warning("Could not find view object with xml_id '%s'" % (xml_id))
                raise ValueError('View %r in website %r not found' % (xml_id, context['website_id']))
        else:
            view_id = super(view, self).get_view_id(cr, uid, xml_id, context=context)
        return view_id

    @api.cr_uid_ids_context
    def render(self, cr, uid, id_or_xml_id, values=None, engine='ir.qweb', context=None):
        if request and getattr(request, 'website_enabled', False):
            engine = 'ir.qweb'

            if isinstance(id_or_xml_id, list):
                id_or_xml_id = id_or_xml_id[0]

            qcontext = self._prepare_qcontext(cr, uid, context=context)

            # add some values
            if values:
                qcontext.update(values)

            # in edit mode ir.ui.view will tag nodes
            if not qcontext.get('translatable') and not qcontext.get('rendering_bundle'):
                if qcontext.get('editable'):
                    context = dict(context, inherit_branding=True)
                elif request.registry['res.users'].has_group(cr, uid, 'base.group_website_publisher'):
                    context = dict(context, inherit_branding_auto=True)

            view_obj = request.website.get_template(id_or_xml_id)
            if 'main_object' not in qcontext:
                qcontext['main_object'] = view_obj

            values = qcontext

        return super(view, self).render(cr, uid, id_or_xml_id, values=values, engine=engine, context=context)

    def _prepare_qcontext(self, cr, uid, context=None):
        if not context:
            context = {}

        company = self.pool['res.company'].browse(cr, SUPERUSER_ID, request.website.company_id.id, context=context)

        editable = request.website.is_publisher()
        translatable = editable and context.get('lang') != request.website.default_lang_code
        editable = not translatable and editable

        qcontext = dict(
            context.copy(),
            website=request.website,
            url_for=website.url_for,
            slug=website.slug,
            res_company=company,
            user_id=self.pool.get("res.users").browse(cr, uid, uid),
            default_lang_code=request.website.default_lang_code,
            languages=request.website.get_languages(),
            translatable=translatable,
            editable=editable,
            menu_data=self.pool['ir.ui.menu'].load_menus_root(cr, uid, context=context) if request.website.is_user() else None,
        )
        return qcontext

    def customize_template_get(self, cr, uid, key, full=False, bundles=False, context=None):
        """ Get inherit view's informations of the template ``key``. By default, only
        returns ``customize_show`` templates (which can be active or not), if
        ``full=True`` returns inherit view's informations of the template ``key``.
        ``bundles=True`` returns also the asset bundles
        """
        imd = self.pool['ir.model.data']
        theme_view_id = imd.xmlid_to_res_id(cr, uid, 'website.theme')
        user = self.pool['res.users'].browse(cr, uid, context=context)
        user_groups = set(user.groups_id)
        views = self._views_get(
            cr, uid, key, bundles=bundles,
            context=dict(context or {}, active_test=False))
        done = set()
        result = []
        for v in views:
            if not user_groups.issuperset(v.groups_id):
                continue
            if full or (v.customize_show and v.inherit_id.id != theme_view_id):
                if v.inherit_id not in done:
                    result.append({
                        'name': v.inherit_id.name,
                        'id': v.id,
                        'key': v.key,
                        'inherit_id': v.inherit_id.id,
                        'header': True,
                        'active': False
                    })
                    done.add(v.inherit_id)
                result.append({
                    'name': v.name,
                    'id': v.id,
                    'key': v.key,
                    'inherit_id': v.inherit_id.id,
                    'header': False,
                    'active': v.active,
                })
        return result
