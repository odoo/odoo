# -*- coding: ascii -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from itertools import groupby
from lxml import etree

from odoo import api, fields, models
from odoo import tools

from odoo.addons.website.models import website
from odoo.http import request

_logger = logging.getLogger(__name__)


class View(models.Model):

    _name = "ir.ui.view"
    _inherit = ["ir.ui.view", "website.seo.metadata"]

    page = fields.Boolean("Whether this view is a web page template (complete)", default=False)
    customize_show = fields.Boolean("Show As Optional Inherit", default=False)
    website_id = fields.Many2one('website', ondelete='cascade', string="Website")

    @api.multi
    def unlink(self):
        result = super(View, self).unlink()
        self.clear_caches()
        return result

    @api.multi
    def _sort_suitability_key(self):
        """ Key function to sort views by descending suitability
            Suitability of a view is defined as follow:
                * if the view and request website_id are matched
                * then if the view has no set website
        """
        self.ensure_one()
        context_website_id = self.env.context.get('website_id', 1)
        website_id = self.website_id.id or 0
        different_website = context_website_id != website_id
        return (different_website, website_id)

    def filter_duplicate(self):
        """ Filter current recordset only keeping the most suitable view per distinct key """
        filtered = self.env['ir.ui.view']
        for dummy, group in groupby(self, key=lambda record: record.key):
            filtered += sorted(group, key=lambda record: record._sort_suitability_key())[0]
        return filtered

    @api.model
    def _view_obj(self, view_id):
        if isinstance(view_id, basestring):
            if 'website_id' in self._context:
                domain = [('key', '=', view_id), '|', ('website_id', '=', False), ('website_id', '=', self._context.get('website_id'))]
                order = 'website_id'
            else:
                domain = [('key', '=', view_id)]
                order = self._order
            views = self.search(domain, order=order)
            if views:
                return views.filter_duplicate()
            else:
                return self.env.ref(view_id)
        elif isinstance(view_id, (int, long)):
            return self.browse(view_id)

        # assume it's already a view object (WTF?)
        return view_id

    @api.model
    @tools.ormcache_context('self._uid', 'xml_id', keys=('website_id',))
    def get_view_id(self, xml_id):
        if 'website_id' in self._context and not isinstance(xml_id, (int, long)):
            domain = [('key', '=', xml_id), '|', ('website_id', '=', self._context['website_id']), ('website_id', '=', False)]
            view = self.search(domain, order='website_id', limit=1)
            if not view:
                _logger.warning("Could not find view object with xml_id '%s'", xml_id)
                raise ValueError('View %r in website %r not found' % (xml_id, self._context['website_id']))
            return view.id
        return super(View, self).get_view_id(xml_id)

    @api.multi
    def render(self, values=None, engine='ir.qweb'):
        """ Render the template. If website is enabled on request, then extend rendering context with website values. """
        new_context = dict(self._context)
        if request and getattr(request, 'website_enabled', False):

            qcontext = self._prepare_qcontext()

            # add some values
            if values:
                qcontext.update(values)

            # in edit mode ir.ui.view will tag nodes
            if not qcontext.get('translatable') and not qcontext.get('rendering_bundle'):
                if qcontext.get('editable'):
                    new_context = dict(self._context, inherit_branding=True)
                elif request.env.user.has_group('website.group_website_publisher'):
                    new_context = dict(self._context, inherit_branding_auto=True)

            if 'main_object' not in qcontext:
                qcontext['main_object'] = self

            values = qcontext

        if self._context != new_context:
            self = self.with_context(new_context)
        return super(View, self).render(values, engine=engine)

    @api.model
    def _prepare_qcontext(self):
        """ Returns the qcontext : rendering context with website specific value (required
            to render website layout template)
        """
        company = request.website.company_id.sudo()

        editable = request.website.is_publisher()
        translatable = editable and self._context.get('lang') != request.website.default_lang_code
        editable = not translatable and editable

        qcontext = dict(
            self._context.copy(),
            website=request.website,
            url_for=website.url_for,
            slug=website.slug,
            res_company=company,
            user_id=self.env["res.users"].browse(self.env.user.id),
            default_lang_code=request.website.default_lang_code,
            languages=request.website.get_languages(),
            translatable=translatable,
            editable=editable,
            menu_data=self.env['ir.ui.menu'].load_menus_root() if request.website.is_user() else None,
        )
        return qcontext

    @api.model
    def _customize_template_get_views(self, key, full=False, bundles=False):
        """ Get inherit view's informations of the template ``key``.
            returns views (which can be active or not)
            ``full=False`` returns only the customize_show template
            ``bundles=True`` returns also the asset bundles
        """
        views = super(View, self)._customize_template_get_views(key, full=full, bundles=bundles)
        if full:
            return views
        return views.filtered(lambda v: v.customize_show)
