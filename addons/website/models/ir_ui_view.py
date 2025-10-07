# Part of Odoo. See LICENSE file for full copyright and licensing details.

import copy
import logging
import uuid
import werkzeug
from lxml import etree, html


from odoo import api, fields, models, _
from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.fields import Domain
from odoo.http import request
from odoo.addons.base.models.ir_ui_view import MOVABLE_BRANDING

_logger = logging.getLogger(__name__)

EDITING_ATTRIBUTES = MOVABLE_BRANDING + [
    'data-oe-type',
    'data-oe-expression',
    'data-oe-translation-id',
    'data-note-id'
]


class IrUiView(models.Model):
    _name = 'ir.ui.view'

    _inherit = ["ir.ui.view", "website.seo.metadata"]

    website_id = fields.Many2one('website', ondelete='cascade', string="Website")
    page_ids = fields.One2many('website.page', 'view_id')
    controller_page_ids = fields.One2many('website.controller.page', 'view_id')
    first_page_id = fields.Many2one('website.page', string='Website Page', help='First page linked to this view', compute='_compute_first_page_id')
    track = fields.Boolean(string='Track', default=False, help="Allow to specify for one page of the website to be trackable or not")
    visibility = fields.Selection(
        [
            ('', 'Public'),
            ('connected', 'Signed In'),
            ('restricted_group', 'Restricted Group'),
            ('password', 'With Password')
        ],
        default='',
    )
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
                r.sudo().visibility_password = (r.visibility_password_display and crypt_context.hash(r.visibility_password_display)) or ''
                r.visibility = r.visibility  # double check access

    def _compute_first_page_id(self):
        for view in self:
            view.first_page_id = self.env['website.page'].search([('view_id', 'in', view.ids)], limit=1)

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

    @api.depends('website_id', 'key')
    @api.depends_context('display_key', 'display_website')
    def _compute_display_name(self):
        if not (self.env.context.get('display_key') or self.env.context.get('display_website')):
            return super()._compute_display_name()

        for view in self:
            view_name = view.name
            if self.env.context.get('display_key'):
                view_name += ' <%s>' % view.key
            if self.env.context.get('display_website') and view.website_id:
                view_name += ' [%s]' % view.website_id.name
            view.display_name = view_name

    def write(self, vals):
        '''COW for ir.ui.view. This way editing websites does not impact other
        websites. Also this way newly created websites will only
        contain the default views.
        '''
        current_website_id = self.env.context.get('website_id')
        if not current_website_id or self.env.context.get('no_cow'):
            return super().write(vals)

        # We need to consider inactive views when handling multi-website cow
        # feature (to copy inactive children views, to search for specific
        # views, ...)
        # Website-specific views need to be updated first because they might
        # be relocated to new ids by the cow if they are involved in the
        # inheritance tree.
        for view in self.with_context(active_test=False).sorted('website_id.id'):
            # Make sure views which are written in a website context receive
            # a value for their 'key' field
            if not view.key and not vals.get('key'):
                view.with_context(no_cow=True).key = 'website.key_%s' % str(uuid.uuid4())[:6]

            pages = view.page_ids

            # No need of COW if the view is already specific
            if view.website_id:
                super(IrUiView, view).write(vals)
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
                super(IrUiView, website_specific_view).write(vals)
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

            super(IrUiView, website_specific_view).write(vals)

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
        super()._create_all_specific_views(processed_modules)

    def unlink(self):
        '''This implements COU (copy-on-unlink). When deleting a generic page
        website-specific pages will be created so only the current
        website is affected.
        '''
        current_website_id = self.env.context.get('website_id')

        if current_website_id and not self.env.context.get('no_cow'):
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

        result = super(IrUiView, self + specific_views).unlink()
        self.env.registry.clear_cache('templates')
        return result

    def _create_website_specific_pages_for_view(self, new_view, website):
        for page in self.page_ids:
            # create new pages for this view
            new_page = page.copy({
                'view_id': new_view.id,
                'is_published': page.is_published,
            })
            page.menu_ids.filtered(lambda m: m.website_id.id == website.id).page_id = new_page.id

    def get_view_hierarchy(self):
        self.ensure_one()
        top_level_view = self
        while top_level_view.inherit_id:
            top_level_view = top_level_view.inherit_id
        top_level_view = top_level_view.with_context(active_test=False)
        sibling_views = top_level_view.search_read([('key', '=', top_level_view.key), ('id', '!=', top_level_view.id)])
        return {
            'sibling_views': sibling_views,
            'hierarchy': top_level_view._build_hierarchy_datastructure()
        }

    def _build_hierarchy_datastructure(self):
        inherit_children = []
        for child in self.inherit_children_ids:
            inherit_children.append(child._build_hierarchy_datastructure())
        return {
            'id': self.id,
            'name': self.name,
            'inherit_children': inherit_children,
            'arch_updated': self.arch_updated,
            'website_name': self.website_id.name if self.website_id else False,
            'active': self.active,
            'key': self.key,
        }

    @api.model
    def get_related_views(self, key, bundles=False):
        '''Make this only return most specific views for website.'''
        # get_related_views can be called through website=False routes
        # (e.g. /website/get_assets_editor_resources), so website
        # dispatch_parameters may not be added. Manually set
        # website_id. (It will then always fallback on a website, this
        # method should never be called in a generic context, even for
        # tests)
        current_website = self.env['website'].get_current_website()
        return super(IrUiView, self.with_context(
            website_id=current_website.id
        )).get_related_views(key, bundles=bundles).with_context(
            lang=current_website.default_lang_id.code,
        )

    def filter_duplicate(self):
        """ Filter current recordset only keeping the most suitable view per distinct key.
            Every non-accessible view will be removed from the set:

              * In non website context, every view with a website will be removed
              * In a website context, every view from another website
        """
        current_website_id = self.env.context.get('website_id')
        if not current_website_id:
            return self.filtered(lambda view: not view.website_id)

        specific_views_keys = {view.key for view in self if view.website_id.id == current_website_id and view.key}
        most_specific_views = []
        for view in self:
            # specific view: add it if it's for the current website and ignore
            # it if it's for another website
            if view.website_id and view.website_id.id == current_website_id:
                most_specific_views.append(view)
            # generic view: add it only if, for the current website, there is no
            # specific view for this view (based on the same `key` attribute)
            elif not view.website_id and view.key not in specific_views_keys:
                most_specific_views.append(view)

        return self.browse().union(*most_specific_views)

    @api.model
    def _view_get_inherited_children(self, view):
        extensions = super()._view_get_inherited_children(view)
        return extensions.filter_duplicate()

    @api.model
    def _get_inheriting_views_domain(self):
        domain = super()._get_inheriting_views_domain()
        current_website = self.env['website'].browse(self.env.context.get('website_id'))
        website_views_domain = current_website.website_domain()
        # when rendering for the website we have to include inactive views
        # we will prefer inactive website-specific views over active generic ones
        if current_website:
            domain = domain.map_conditions(lambda cond: cond if cond.field_expr != 'active' else Domain.TRUE)
        return website_views_domain & domain

    @api.model
    def _get_inheriting_views(self):
        if not self.env.context.get('website_id'):
            return super()._get_inheriting_views()

        views = super(IrUiView, self.with_context(active_test=False))._get_inheriting_views()
        # prefer inactive website-specific views over active generic ones
        return views.filter_duplicate().filtered('active')

    @api.model
    def _get_filter_xmlid_query(self):
        """This method add some specific view that do not have XML ID
        """
        if not self.env.context.get('website_id'):
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
    def _get_cached_template_prefetched_keys(self):
        return super()._get_cached_template_prefetched_keys() + ['active', 'visibility', 'track']

    @api.model
    def _get_template_minimal_cache_keys(self):
        return super()._get_template_minimal_cache_keys() + (self.env.context.get('website_id'),)

    @api.model
    def _get_template_domain(self, xmlids):
        """ If a website_id is in the context and the given xml_id then try
            to get the id of the specific view for that website, but fallback
            to the id of the generic view if there is no specific.
            If no website_id is in the context, every view with a website will
            be filtered out.

            Archived views are ignored (unless the active_test context is set, but
            then the ormcache will not work as expected).
        """
        domain = super()._get_template_domain(xmlids)
        return domain & Domain('website_id', 'in', (False, self.env.context.get('website_id', False)))

    @api.model
    def _fetch_template_views(self, ids_or_xmlids):
        data = super()._fetch_template_views(ids_or_xmlids)
        for key in list(data):
            if isinstance(data[key], MissingError):
                data[key] = MissingError(self.env._("%(error)s (website: %(website_id)s)", error=data[key], website_id=self.env.context.get('website_id')))
        return data

    @api.model
    def _get_template_order(self):
        return f"website_id asc, {super()._get_template_order()}"

    def _get_cached_visibility(self):
        info = self._get_cached_template_info(self.id, _view=self)
        if info['error']:
            raise info['error']
        return info['visibility']

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

    @api.readonly
    @api.model
    def render_public_asset(self, template, values=None):
        # to get the specific asset for access checking
        if request and hasattr(request, 'website'):
            return super(IrUiView, self.with_context(website_id=request.website.id)).render_public_asset(template, values=values)
        return super().render_public_asset(template, values=values)

    def _render_template(self, template, values=None):
        """ Render the template. If website is enabled on request, then extend rendering context with website values. """
        view = self._get_template_view(template).sudo()
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
            return False

    def _read_template_keys(self):
        return super()._read_template_keys() + ['website_id']

    # ------------------------------------------------------
    # Save from html
    # ------------------------------------------------------

    def _get_cleaned_non_editing_attributes(self, attributes):
        """
        Returns a new mapping of attributes -> value without the parts that are
        not meant to be saved (branding, editing classes, ...). Note that
        classes are meant to be cleaned on the client side before saving as
        mostly linked to the related options (so we are not supposed to know
        which to remove here).

        :param attributes: a mapping of attributes -> value
        :return: a new mapping of attributes -> value
        """
        attributes = {k: v for k, v in attributes if k not in EDITING_ATTRIBUTES}
        if 'class' in attributes:
            classes = attributes['class'].split()
            attributes['class'] = ' '.join([c for c in classes if c != 'o_editable'])
        if attributes.get('contenteditable') == 'true':
            del attributes['contenteditable']
        return attributes

    @api.model
    def extract_embedded_fields(self, arch):
        return arch.xpath('//*[@data-oe-model != "ir.ui.view"]')

    @api.model
    def extract_oe_structures(self, arch):
        return arch.xpath('//*[hasclass("oe_structure")][contains(@id, "oe_structure")]')

    @api.model
    def save_embedded_field(self, el):
        Model = self.env[el.get('data-oe-model')]
        field = el.get('data-oe-field')

        model = 'ir.qweb.field.' + el.get('data-oe-type')
        converter = self.env[model] if model in self.env else self.env['ir.qweb.field']

        try:
            value = converter.from_html(Model, Model._fields[field], el)
            if value is not None:
                # TODO: batch writes?
                record = Model.browse(int(el.get('data-oe-id')))
                if not self.env.context.get('lang') and self.get_default_lang_code():
                    record.with_context(lang=self.get_default_lang_code()).write({field: value})
                else:
                    record.write({field: value})

                if callable(Model._fields[field].translate):
                    self._copy_custom_snippet_translations(record, field)

        except (ValueError, TypeError):
            raise ValidationError(_(
                "Invalid field value for %(field_name)s: %(value)s",
                field_name=Model._fields[field].string,
                value=el.text_content().strip(),
            ))

    def save_oe_structure(self, el):
        self.ensure_one()

        if el.get('id') in self.key:
            # Do not inherit if the oe_structure already has its own inheriting view
            return False

        arch = etree.Element('data')
        xpath = etree.Element('xpath', expr="//*[hasclass('oe_structure')][@id='{}']".format(el.get('id')), position="replace")
        arch.append(xpath)
        attributes = self._get_cleaned_non_editing_attributes(el.attrib.items())
        structure = etree.Element(el.tag, attrib=attributes)
        structure.text = el.text
        xpath.append(structure)
        for child in el.iterchildren(tag=etree.Element):
            structure.append(copy.deepcopy(child))

        vals = {
            'inherit_id': self.id,
            'name': '%s (%s)' % (self.name, el.get('id')),
            'arch': etree.tostring(arch, encoding='unicode'),
            'key': '%s_%s' % (self.key, el.get('id')),
            'type': 'qweb',
            'mode': 'extension',
        }
        vals.update(self._save_oe_structure_hook())
        oe_structure_view = self.env['ir.ui.view'].create(vals)
        self._copy_custom_snippet_translations(oe_structure_view, 'arch_db')

        return True

    @api.model
    def _copy_custom_snippet_translations(self, record, html_field):
        """ Given a ``record`` and its HTML ``field``, detect any
        usage of a custom snippet and copy its translations.
        """
        lang_value = record[html_field]
        if not lang_value:
            return

        try:
            tree = html.fromstring(lang_value)
        except etree.ParserError as e:
            raise ValidationError(str(e))

        for custom_snippet_el in tree.xpath('//*[hasclass("s_custom_snippet")]'):
            custom_snippet_name = custom_snippet_el.get('data-name')
            custom_snippet_view = self.search([('name', '=', custom_snippet_name)], limit=1)
            if custom_snippet_view:
                self._copy_field_terms_translations(custom_snippet_view, 'arch_db', record, html_field)

    @api.model
    def _copy_field_terms_translations(self, records_from, name_field_from, record_to, name_field_to):
        """ Copy model terms translations from ``records_from.name_field_from``
        to ``record_to.name_field_to`` for all activated languages if the term
        in ``record_to.name_field_to`` is untranslated (the term matches the
        one in the current language).

        For instance, copy the translations of a
        ``product.template.html_description`` field to a ``ir.ui.view.arch_db``
        field.

        The method takes care of read and write access of both records/fields.
        """
        record_to.check_access('write')
        field_from = records_from._fields[name_field_from]
        field_to = record_to._fields[name_field_to]
        record_to._check_field_access(field_to, 'write')

        error_callable_msg = "'translate' property of field %r is not callable"
        if not callable(field_from.translate):
            raise TypeError(error_callable_msg % field_from)
        if not callable(field_to.translate):
            raise TypeError(error_callable_msg % field_to)
        if not field_to.store:
            raise ValueError("Field %r is not stored" % field_to)

        # This will also implicitly check for `read` access rights
        if not record_to[name_field_to] or not any(records_from.mapped(name_field_from)):
            return

        lang_env = self.env.lang or 'en_US'
        langs = {lang for lang, _ in self.env['res.lang'].get_installed()}

        # 1. Get translations
        records_from.flush_model([name_field_from])
        existing_translation_dictionary = field_to.get_translation_dictionary(
            record_to[name_field_to],
            {lang: record_to.with_context(prefetch_langs=True, lang=lang)[name_field_to] for lang in langs if lang != lang_env}
        )
        extra_translation_dictionary = {}
        for record_from in records_from:
            extra_translation_dictionary.update(field_from.get_translation_dictionary(
                record_from[name_field_from],
                {lang: record_from.with_context(prefetch_langs=True, lang=lang)[name_field_from] for lang in langs if lang != lang_env}
            ))
        for term, extra_translation_values in extra_translation_dictionary.items():
            existing_translation_values = existing_translation_dictionary.setdefault(term, {})
            # Update only default translation values that aren't customized by the user.
            for lang, extra_translation in extra_translation_values.items():
                if existing_translation_values.get(lang, term) == term:
                    existing_translation_values[lang] = extra_translation
        translation_dictionary = existing_translation_dictionary

        # The `en_US` jsonb value should always be set, even if english is not
        # installed. If we don't do this, the custom snippet `arch_db` will only
        # have a `fr_BE` key but no `en_US` key.
        langs.add('en_US')

        # 2. Set translations
        new_value = {
            lang: field_to.translate(lambda term: translation_dictionary.get(term, {}).get(lang), record_to[name_field_to])
            for lang in langs
        }
        record_to.env.cache.update_raw(record_to, field_to, [new_value], dirty=True)
        # Call `write` to trigger compute etc (`modified()`)
        record_to[name_field_to] = new_value[lang_env]

    @api.model
    def _are_archs_equal(self, arch1, arch2):
        # Note that comparing the strings would not be ok as attributes order
        # must not be relevant
        if arch1.tag != arch2.tag:
            return False
        if arch1.text != arch2.text:
            return False
        if arch1.tail != arch2.tail:
            return False
        if arch1.attrib != arch2.attrib:
            return False
        if len(arch1) != len(arch2):
            return False
        return all(self._are_archs_equal(arch1, arch2) for arch1, arch2 in zip(arch1, arch2))

    def replace_arch_section(self, section_xpath, replacement, replace_tail=False):
        # the root of the arch section shouldn't actually be replaced as it's
        # not really editable itself, only the content truly is editable.
        self.ensure_one()
        arch = etree.fromstring(self.arch.encode('utf-8'))
        # => get the replacement root
        if not section_xpath:
            root = arch
        else:
            # ensure there's only one match
            [root] = arch.xpath(section_xpath)

        root.text = replacement.text

        # We need to replace some attrib for styles changes on the root element
        for attribute in self._get_allowed_root_attrs():
            if attribute in replacement.attrib:
                root.attrib[attribute] = replacement.attrib[attribute]
            elif attribute in root.attrib:
                del root.attrib[attribute]

        # Note: after a standard edition, the tail *must not* be replaced
        if replace_tail:
            root.tail = replacement.tail
        # replace all children
        del root[:]
        for child in replacement:
            root.append(copy.deepcopy(child))

        return arch

    @api.model
    def to_field_ref(self, el):
        # filter out meta-information inserted in the document
        attributes = {k: v for k, v in el.attrib.items()
                           if not k.startswith('data-oe-')}
        attributes['t-field'] = el.get('data-oe-expression')

        out = html.html_parser.makeelement(el.tag, attrib=attributes)
        out.tail = el.tail
        return out

    @api.model
    def to_empty_oe_structure(self, el):
        out = html.html_parser.makeelement(el.tag, attrib=el.attrib)
        out.tail = el.tail
        return out

    @api.model
    def _save_oe_structure_hook(self):
        res = {}
        res['website_id'] = self.env['website'].get_current_website().id
        return res

    @api.model
    def _set_noupdate(self):
        '''If website is installed, any call to `save` from the frontend will
        actually write on the specific view (or create it if not exist yet).
        In that case, we don't want to flag the generic view as noupdate.
        '''
        if not self.env.context.get('website_id'):
            self.sudo().mapped('model_data_id').write({'noupdate': True})

    def save(self, value, xpath=None):
        """ Update a view section. The view section may embed fields to write

        Note that `self` record might not exist when saving an embed field

        :param str xpath: valid xpath to the tag to replace
        """
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
        arch_section = html.fromstring(value)

        if xpath is None:
            # value is an embedded field on its own, not a view section
            self.save_embedded_field(arch_section)
            return

        for el in self.extract_embedded_fields(arch_section):
            self.save_embedded_field(el)

            # transform embedded field back to t-field
            el.getparent().replace(el, self.to_field_ref(el))

        for el in self.extract_oe_structures(arch_section):
            if self.save_oe_structure(el):
                # empty oe_structure in parent view
                empty = self.to_empty_oe_structure(el)
                if el == arch_section:
                    arch_section = empty
                else:
                    el.getparent().replace(el, empty)

        new_arch = self.replace_arch_section(xpath, arch_section)
        old_arch = etree.fromstring(self.arch.encode('utf-8'))
        if not self._are_archs_equal(old_arch, new_arch):
            self._set_noupdate()
            self.write({'arch': etree.tostring(new_arch, encoding='unicode')})
            self._copy_custom_snippet_translations(self, 'arch_db')

    @api.model
    def _get_allowed_root_attrs(self):
        # Related to these options:
        # background-video, background-shapes, parallax, visibility
        return ['style', 'class', 'target', 'href'] + [
            'data-bg-video-src', 'data-shape', 'data-scroll-background-ratio',
            'data-visibility', 'data-visibility-id', 'data-visibility-selectors',
        ] + [
            'data-visibility-value-' + param + suffix
            for param in ('country', 'lang', 'logged', 'utm-campaign', 'utm-medium', 'utm-source')
            for suffix in ('', '-rule')
        ]

    # --------------------------------------------------------------------------
    # Snippet saving
    # --------------------------------------------------------------------------

    @api.model
    def _snippet_save_view_values_hook(self):
        res = {}
        website_id = self.env.context.get('website_id')
        if website_id:
            res['website_id'] = website_id
        return res

    @api.model
    def _get_snippet_addition_view_key(self, template_key, key):
        return '%s.%s' % (template_key, key)

    def _find_available_name(self, name, used_names):
        attempt = 1
        candidate_name = name
        while candidate_name in used_names:
            attempt += 1
            candidate_name = f"{name} ({attempt})"
        return candidate_name

    @api.model
    def save_snippet(self, name, arch, template_key, snippet_key, thumbnail_url):
        """
        Saves a new snippet arch so that it appears with the given name when
        using the given snippets template.

        :param name: the name of the snippet to save
        :param arch: the html structure of the snippet to save
        :param template_key: the key of the view regrouping all snippets in
            which the snippet to save is meant to appear
        :param snippet_key: the key (without module part) to identify
            the snippet from which the snippet to save originates
        :param thumbnail_url: the url of the thumbnail to use when displaying
            the snippet to save
        """
        app_name = template_key.split('.')[0]
        snippet_key = '%s_%s' % (snippet_key, uuid.uuid4().hex)
        full_snippet_key = '%s.%s' % (app_name, snippet_key)

        # find available name
        current_website = self.env['website'].browse(self.env.context.get('website_id'))
        website_domain = Domain(current_website.website_domain())
        used_names = self.search(Domain('name', '=like', '%s%%' % name) & website_domain).mapped('name')
        name = self._find_available_name(name, used_names)

        # html to xml to add '/' at the end of self closing tags like br, ...
        arch_tree = html.fromstring(arch)
        attributes = self._get_cleaned_non_editing_attributes(arch_tree.attrib.items())
        for attr in arch_tree.attrib:
            if attr in attributes:
                arch_tree.attrib[attr] = attributes[attr]
            else:
                del arch_tree.attrib[attr]
        xml_arch = etree.tostring(arch_tree, encoding='utf-8')
        new_snippet_view_values = {
            'name': name,
            'key': full_snippet_key,
            'type': 'qweb',
            'arch': xml_arch,
        }
        new_snippet_view_values.update(self._snippet_save_view_values_hook())
        custom_snippet_view = self.create(new_snippet_view_values)
        model = self.env.context.get('model')
        field = self.env.context.get('field')
        if field == 'arch':
            # Special case for `arch` which is a kind of related (through a
            # compute) to `arch_db` but which is hosting XML/HTML content while
            # being a char field.. Which is then messing around with the
            # `get_translation_dictionary` call, returning XML instead of
            # strings
            field = 'arch_db'
        res_id = self.env.context.get('resId')
        if model and field and res_id:
            self._copy_field_terms_translations(
                self.env[model].browse(int(res_id)),
                field,
                custom_snippet_view,
                'arch_db',
            )

        custom_section = self.search([('key', '=', template_key)])
        snippet_addition_view_values = {
            'name': name + ' Block',
            'key': self._get_snippet_addition_view_key(template_key, snippet_key),
            'inherit_id': custom_section.id,
            'type': 'qweb',
            'arch': """
                <data inherit_id="%s">
                    <xpath expr="//snippets[@id='snippet_custom']" position="inside">
                        <t t-snippet="%s" t-thumbnail="%s"/>
                    </xpath>
                </data>
            """ % (template_key, full_snippet_key, thumbnail_url),
        }
        snippet_addition_view_values.update(self._snippet_save_view_values_hook())
        self.create(snippet_addition_view_values)
        return name

    @api.model
    def rename_snippet(self, name, view_id, template_key):
        snippet_view = self.browse(view_id)
        key = snippet_view.key.split('.')[1]
        custom_key = self._get_snippet_addition_view_key(template_key, key)
        snippet_addition_view = self.search([('key', '=', custom_key)])
        if snippet_addition_view:
            snippet_addition_view.name = name + ' Block'
        snippet_view.name = name

    @api.model
    def delete_snippet(self, view_id, template_key):
        snippet_view = self.browse(view_id)
        key = snippet_view.key.split('.')[1]
        custom_key = self._get_snippet_addition_view_key(template_key, key)
        snippet_addition_view = self.search([('key', '=', custom_key)])
        (snippet_addition_view | snippet_view).unlink()

    # --------------------------------------------------------------------------
    # Languages
    # --------------------------------------------------------------------------

    def _update_field_translations(self, field_name, translations, digest=None, source_lang=''):
        return super(IrUiView, self.with_context(no_cow=True))._update_field_translations(field_name, translations, digest=digest, source_lang=source_lang)

    def _get_base_lang(self):
        """ Returns the default language of the website as the base language if the record is bound to it """
        self.ensure_one()
        website = self.website_id
        if website:
            return website.default_lang_id.code
        return super()._get_base_lang()
