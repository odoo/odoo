# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import uuid
import werkzeug

from odoo import api, fields, models
from odoo import tools
from odoo.exceptions import AccessError
from odoo.osv import expression
from odoo.http import request

_logger = logging.getLogger(__name__)


class View(models.Model):

    _name = "ir.ui.view"
    _inherit = ["ir.ui.view", "website.seo.metadata"]

    website_id = fields.Many2one('website', ondelete='cascade', string="Website")
    page_ids = fields.One2many('website.page', 'view_id')
    first_page_id = fields.Many2one('website.page', string='Website Page', help='First page linked to this view', compute='_compute_first_page_id')
    track = fields.Boolean(string='Track', default=False, help="Allow to specify for one page of the website to be trackable or not")
    visibility = fields.Selection([('', 'All'), ('connected', 'Signed In'), ('restricted_group', 'Restricted Group'), ('password', 'With Password')], default='')
    visibility_password = fields.Char(groups='base.group_system', copy=False)
    visibility_password_display = fields.Char(compute='_get_pwd', inverse='_set_pwd', groups='website.group_website_designer')

    @api.depends('visibility_password')
    def _get_pwd(self):
        for r in self:
            r.visibility_password_display = r.sudo().visibility_password and '********' or ''

    def _set_pwd(self):
        crypt_context = self.env.user._crypt_context()
        for r in self:
            if r.type == 'qweb':
                r.sudo().visibility_password = r.visibility_password_display and crypt_context.encrypt(r.visibility_password_display) or ''
                r.visibility = r.visibility  # double check access

    def _compute_first_page_id(self):
        for view in self:
            view.first_page_id = self.env['website.page'].search([('view_id', '=', view.id)], limit=1)

    @api.model_create_multi
    def create(self, vals_list):
        """
        SOC for ir.ui.view creation. If a view is created without a website_id,
        it should get one if one is present in the context. Also check that
        an explicit website_id in create values matches the one in the context.
        """
        website_id = self.env.context.get('website_id', False)
        if not website_id:
            return super().create(vals_list)

        for vals in vals_list:
            if 'website_id' not in vals:
                # Automatic addition of website ID during view creation if not
                # specified but present in the context
                vals['website_id'] = website_id
            else:
                # If website ID specified, automatic check that it is the same as
                # the one in the context. Otherwise raise an error.
                new_website_id = vals['website_id']
                if not new_website_id:
                    raise ValueError(f"Trying to create a generic view from a website {website_id} environment")
                elif new_website_id != website_id:
                    raise ValueError(f"Trying to create a view for website {new_website_id} from a website {website_id} environment")
        return super().create(vals_list)

    def name_get(self):
        if not (self._context.get('display_key') or self._context.get('display_website')):
            return super(View, self).name_get()

        res = []
        for view in self:
            view_name = view.name
            if self._context.get('display_key'):
                view_name += ' <%s>' % view.key
            if self._context.get('display_website') and view.website_id:
                view_name += ' [%s]' % view.website_id.name
            res.append((view.id, view_name))
        return res

    def write(self, vals):
        '''COW for ir.ui.view. This way editing websites does not impact other
        websites. Also this way newly created websites will only
        contain the default views.
        '''
        current_website_id = self.env.context.get('website_id')
        if not current_website_id or self.env.context.get('no_cow'):
            return super(View, self).write(vals)

        # We need to consider inactive views when handling multi-website cow
        # feature (to copy inactive children views, to search for specific
        # views, ...)
        # Website-specific views need to be updated first because they might
        # be relocated to new ids by the cow if they are involved in the
        # inheritance tree.
        for view in self.with_context(active_test=False).sorted(key='website_id', reverse=True):
            # Make sure views which are written in a website context receive
            # a value for their 'key' field
            if not view.key and not vals.get('key'):
                view.with_context(no_cow=True).key = 'website.key_%s' % str(uuid.uuid4())[:6]

            pages = view.page_ids

            # No need of COW if the view is already specific
            if view.website_id:
                super(View, view).write(vals)
                continue

            # Ensure the cache of the pages stay consistent when doing COW.
            # This is necessary when writing view fields from a page record
            # because the generic page will put the given values on its cache
            # but in reality the values were only meant to go on the specific
            # page. Invalidate all fields and not only those in vals because
            # other fields could have been changed implicitly too.
            pages.flush_recordset()
            pages.invalidate_recordset()

            # If already a specific view for this generic view, write on it
            website_specific_view = view.search([
                ('key', '=', view.key),
                ('website_id', '=', current_website_id)
            ], limit=1)
            if website_specific_view:
                super(View, website_specific_view).write(vals)
                continue

            # Set key to avoid copy() to generate an unique key as we want the
            # specific view to have the same key
            copy_vals = {'website_id': current_website_id, 'key': view.key}
            # Copy with the 'inherit_id' field value that will be written to
            # ensure the copied view's validation works
            if vals.get('inherit_id'):
                copy_vals['inherit_id'] = vals['inherit_id']
            website_specific_view = view.copy(copy_vals)

            view._create_website_specific_pages_for_view(website_specific_view,
                                                         view.env['website'].browse(current_website_id))

            for inherit_child in view.inherit_children_ids.filter_duplicate().sorted(key=lambda v: (v.priority, v.id)):
                if inherit_child.website_id.id == current_website_id:
                    # In the case the child was already specific to the current
                    # website, we cannot just reattach it to the new specific
                    # parent: we have to copy it there and remove it from the
                    # original tree. Indeed, the order of children 'id' fields
                    # must remain the same so that the inheritance is applied
                    # in the same order in the copied tree.
                    child = inherit_child.copy({'inherit_id': website_specific_view.id, 'key': inherit_child.key})
                    inherit_child.inherit_children_ids.write({'inherit_id': child.id})
                    inherit_child.unlink()
                else:
                    # Trigger COW on inheriting views
                    inherit_child.write({'inherit_id': website_specific_view.id})

            super(View, website_specific_view).write(vals)

        return True

    def _load_records_write_on_cow(self, cow_view, inherit_id, values):
        inherit_id = self.search([
            ('key', '=', self.browse(inherit_id).key),
            ('website_id', 'in', (False, cow_view.website_id.id)),
        ], order='website_id', limit=1).id
        values['inherit_id'] = inherit_id
        cow_view.with_context(no_cow=True).write(values)

    def _create_all_specific_views(self, processed_modules):
        """ When creating a generic child view, we should
            also create that view under specific view trees (COW'd).
            Top level view (no inherit_id) do not need that behavior as they
            will be shared between websites since there is no specific yet.
        """
        # Only for the modules being processed
        regex = '^(%s)[.]' % '|'.join(processed_modules)
        # Retrieve the views through a SQl query to avoid ORM queries inside of for loop
        # Retrieves all the views that are missing their specific counterpart with all the
        # specific view parent id and their website id in one query
        query = """
            SELECT generic.id, ARRAY[array_agg(spec_parent.id), array_agg(spec_parent.website_id)]
              FROM ir_ui_view generic
        INNER JOIN ir_ui_view generic_parent ON generic_parent.id = generic.inherit_id
        INNER JOIN ir_ui_view spec_parent ON spec_parent.key = generic_parent.key
         LEFT JOIN ir_ui_view specific ON specific.key = generic.key AND specific.website_id = spec_parent.website_id
             WHERE generic.type='qweb'
               AND generic.website_id IS NULL
               AND generic.key ~ %s
               AND spec_parent.website_id IS NOT NULL
               AND specific.id IS NULL
          GROUP BY generic.id
        """
        self.env.cr.execute(query, (regex, ))
        result = dict(self.env.cr.fetchall())

        for record in self.browse(result.keys()):
            specific_parent_view_ids, website_ids = result[record.id]
            for specific_parent_view_id, website_id in zip(specific_parent_view_ids, website_ids):
                record.with_context(website_id=website_id).write({
                    'inherit_id': specific_parent_view_id,
                })
        super(View, self)._create_all_specific_views(processed_modules)

    def unlink(self):
        '''This implements COU (copy-on-unlink). When deleting a generic page
        website-specific pages will be created so only the current
        website is affected.
        '''
        current_website_id = self._context.get('website_id')

        if current_website_id and not self._context.get('no_cow'):
            for view in self.filtered(lambda view: not view.website_id):
                for w in self.env['website'].search([('id', '!=', current_website_id)]):
                    # reuse the COW mechanism to create
                    # website-specific copies, it will take
                    # care of creating pages and menus.
                    view.with_context(website_id=w.id).write({'name': view.name})

        specific_views = self.env['ir.ui.view']
        if self and self.pool._init:
            for view in self.filtered(lambda view: not view.website_id):
                specific_views += view._get_specific_views()

        result = super(View, self + specific_views).unlink()
        self.clear_caches()
        return result

    def _create_website_specific_pages_for_view(self, new_view, website):
        for page in self.page_ids:
            # create new pages for this view
            new_page = page.copy({
                'view_id': new_view.id,
                'is_published': page.is_published,
            })
            page.menu_ids.filtered(lambda m: m.website_id.id == website.id).page_id = new_page.id

    def _get_top_level_view(self):
        self.ensure_one()
        return self.inherit_id._get_top_level_view() if self.inherit_id else self

    @api.model
    def get_related_views(self, key, bundles=False):
        '''Make this only return most specific views for website.'''
        # get_related_views can be called through website=False routes
        # (e.g. /web_editor/get_assets_editor_resources), so website
        # dispatch_parameters may not be added. Manually set
        # website_id. (It will then always fallback on a website, this
        # method should never be called in a generic context, even for
        # tests)
        self = self.with_context(website_id=self.env['website'].get_current_website().id)
        return super(View, self).get_related_views(key, bundles=bundles)

    def filter_duplicate(self):
        """ Filter current recordset only keeping the most suitable view per distinct key.
            Every non-accessible view will be removed from the set:
              * In non website context, every view with a website will be removed
              * In a website context, every view from another website
        """
        current_website_id = self._context.get('website_id')
        most_specific_views = self.env['ir.ui.view']
        if not current_website_id:
            return self.filtered(lambda view: not view.website_id)

        for view in self:
            # specific view: add it if it's for the current website and ignore
            # it if it's for another website
            if view.website_id and view.website_id.id == current_website_id:
                most_specific_views |= view
            # generic view: add it only if, for the current website, there is no
            # specific view for this view (based on the same `key` attribute)
            elif not view.website_id and not any(view.key == view2.key and view2.website_id and view2.website_id.id == current_website_id for view2 in self):
                most_specific_views |= view

        return most_specific_views

    @api.model
    def _view_get_inherited_children(self, view):
        extensions = super(View, self)._view_get_inherited_children(view)
        return extensions.filter_duplicate()

    @api.model
    def _view_obj(self, view_id):
        ''' Given an xml_id or a view_id, return the corresponding view record.
            In case of website context, return the most specific one.
            :param view_id: either a string xml_id or an integer view_id
            :return: The view record or empty recordset
        '''
        if isinstance(view_id, str) or isinstance(view_id, int):
            return self.env['website'].viewref(view_id)
        else:
            # It can already be a view object when called by '_views_get()' that is calling '_view_obj'
            # for it's inherit_children_ids, passing them directly as object record. (Note that it might
            # be a view_id from another website but it will be filtered in 'get_related_views()')
            return view_id if view_id._name == 'ir.ui.view' else self.env['ir.ui.view']

    @api.model
    def _get_inheriting_views_domain(self):
        domain = super(View, self)._get_inheriting_views_domain()
        current_website = self.env['website'].browse(self._context.get('website_id'))
        website_views_domain = current_website.website_domain()
        # when rendering for the website we have to include inactive views
        # we will prefer inactive website-specific views over active generic ones
        if current_website:
            domain = [leaf for leaf in domain if 'active' not in leaf]
        return expression.AND([website_views_domain, domain])

    @api.model
    def _get_inheriting_views(self):
        if not self._context.get('website_id'):
            return super(View, self)._get_inheriting_views()

        views = super(View, self.with_context(active_test=False))._get_inheriting_views()
        # prefer inactive website-specific views over active generic ones
        return views.filter_duplicate().filtered('active')

    @api.model
    def _get_filter_xmlid_query(self):
        """This method add some specific view that do not have XML ID
        """
        if not self._context.get('website_id'):
            return super()._get_filter_xmlid_query()
        else:
            return """SELECT res_id
                    FROM   ir_model_data
                    WHERE  res_id IN %(res_ids)s
                        AND model = 'ir.ui.view'
                        AND module  IN %(modules)s
                    UNION
                    SELECT sview.id
                    FROM   ir_ui_view sview
                        INNER JOIN ir_ui_view oview USING (key)
                        INNER JOIN ir_model_data d
                                ON oview.id = d.res_id
                                    AND d.model = 'ir.ui.view'
                                    AND d.module  IN %(modules)s
                    WHERE  sview.id IN %(res_ids)s
                        AND sview.website_id IS NOT NULL
                        AND oview.website_id IS NULL;
                    """

    @api.model
    @tools.ormcache_context('self.env.uid', 'self.env.su', 'xml_id', keys=('website_id',))
    def _get_view_id(self, xml_id):
        """If a website_id is in the context and the given xml_id is not an int
        then try to get the id of the specific view for that website, but
        fallback to the id of the generic view if there is no specific.

        If no website_id is in the context, it might randomly return the generic
        or the specific view, so it's probably not recommanded to use this
        method. `viewref` is probably more suitable.

        Archived views are ignored (unless the active_test context is set, but
        then the ormcache_context will not work as expected).
        """
        website_id = self._context.get('website_id')
        if website_id and not isinstance(xml_id, int):
            current_website = self.env['website'].browse(int(website_id))
            domain = ['&', ('key', '=', xml_id)] + current_website.website_domain()

            view = self.sudo().search(domain, order='website_id', limit=1)
            if not view:
                _logger.warning("Could not find view object with xml_id '%s'", xml_id)
                raise ValueError('View %r in website %r not found' % (xml_id, self._context['website_id']))
            return view.id
        return super(View, self.sudo())._get_view_id(xml_id)

    @tools.ormcache('self.id')
    def _get_cached_visibility(self):
        return self.visibility

    def _handle_visibility(self, do_raise=True):
        """ Check the visibility set on the main view and raise 403 if you should not have access.
            Order is: Public, Connected, Has group, Password

            It only check the visibility on the main content, others views called stay available in rpc.
        """
        error = False

        self = self.sudo()

        visibility = self._get_cached_visibility()

        if visibility and not request.env.user.has_group('website.group_website_designer'):
            if (visibility == 'connected' and request.website.is_public_user()):
                error = werkzeug.exceptions.Forbidden()
            elif visibility == 'password' and \
                    (request.website.is_public_user() or self.id not in request.session.get('views_unlock', [])):
                pwd = request.params.get('visibility_password')
                if pwd and self.env.user._crypt_context().verify(
                        pwd, self.visibility_password):
                    request.session.setdefault('views_unlock', list()).append(self.id)
                else:
                    error = werkzeug.exceptions.Forbidden('website_visibility_password_required')

            if visibility not in ('password', 'connected'):
                try:
                    self._check_view_access()
                except AccessError:
                    error = werkzeug.exceptions.Forbidden()

        if error:
            if do_raise:
                raise error
            else:
                return False
        return True

    def _render_template(self, template, values=None):
        """ Render the template. If website is enabled on request, then extend rendering context with website values. """
        view = self._get(template).sudo()
        view._handle_visibility(do_raise=True)
        if values is None:
            values = {}
        if 'main_object' not in values:
            values['main_object'] = view
        return super()._render_template(template, values=values)

    @api.model
    def get_default_lang_code(self):
        website_id = self.env.context.get('website_id')
        if website_id:
            lang_code = self.env['website'].browse(website_id).default_lang_id.code
            return lang_code
        else:
            return super(View, self).get_default_lang_code()

    def _read_template_keys(self):
        return super(View, self)._read_template_keys() + ['website_id']

    @api.model
    def _save_oe_structure_hook(self):
        res = super(View, self)._save_oe_structure_hook()
        res['website_id'] = self.env['website'].get_current_website().id
        return res

    @api.model
    def _set_noupdate(self):
        '''If website is installed, any call to `save` from the frontend will
        actually write on the specific view (or create it if not exist yet).
        In that case, we don't want to flag the generic view as noupdate.
        '''
        if not self._context.get('website_id'):
            super(View, self)._set_noupdate()

    def save(self, value, xpath=None):
        self.ensure_one()
        current_website = self.env['website'].get_current_website()
        # xpath condition is important to be sure we are editing a view and not
        # a field as in that case `self` might not exist (check commit message)
        if xpath and self.key and current_website:
            # The first time a generic view is edited, if multiple editable parts
            # were edited at the same time, multiple call to this method will be
            # done but the first one may create a website specific view. So if there
            # already is a website specific view, we need to divert the super to it.
            website_specific_view = self.env['ir.ui.view'].search([
                ('key', '=', self.key),
                ('website_id', '=', current_website.id)
            ], limit=1)
            if website_specific_view:
                self = website_specific_view
        super(View, self).save(value, xpath=xpath)

    @api.model
    def _get_allowed_root_attrs(self):
        # Related to these options:
        # background-video, background-shapes, parallax
        return super()._get_allowed_root_attrs() + [
            'data-bg-video-src', 'data-shape', 'data-scroll-background-ratio',
        ]

    # --------------------------------------------------------------------------
    # Snippet saving
    # --------------------------------------------------------------------------

    @api.model
    def _snippet_save_view_values_hook(self):
        res = super()._snippet_save_view_values_hook()
        website_id = self.env.context.get('website_id')
        if website_id:
            res['website_id'] = website_id
        return res

    def _update_field_translations(self, fname, translations, digest=None):
        return super(View, self.with_context(no_cow=True))._update_field_translations(fname, translations, digest)

    def _get_base_lang(self):
        """ Returns the default language of the website as the base language if the record is bound to it """
        self.ensure_one()
        website = self.website_id
        if website:
            return website.default_lang_id.code
        return super()._get_base_lang()
