# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models, _
from odoo.fields import Domain
from odoo.addons.website.tools import text_from_html
from odoo.http import request
from odoo.exceptions import AccessError, UserError
from odoo.tools import escape_psql
from odoo.tools import split_every
from odoo.tools.urls import urljoin as url_join
from odoo.tools.json import scriptsafe as json_safe


class WebsiteSeoMetadata(models.AbstractModel):
    _name = 'website.seo.metadata'

    _description = 'SEO metadata'

    is_seo_optimized = fields.Boolean("SEO optimized", compute='_compute_is_seo_optimized', store=True)
    website_meta_title = fields.Char("Website meta title", translate=True, prefetch="website_meta")
    website_meta_description = fields.Text("Website meta description", translate=True, prefetch="website_meta")
    website_meta_keywords = fields.Char("Website meta keywords", translate=True, prefetch="website_meta")
    website_meta_og_img = fields.Char("Website opengraph image")
    seo_name = fields.Char("Seo name", translate=True, prefetch=True)

    @api.depends("website_meta_title", "website_meta_description", "website_meta_keywords")
    def _compute_is_seo_optimized(self):
        for record in self:
            record.is_seo_optimized = record.website_meta_title and record.website_meta_description and record.website_meta_keywords

    def _default_website_meta(self):
        """ This method will return default meta information. It return the dict
            contains meta property as a key and meta content as a value.
            e.g. 'og:type': 'website'.

            Override this method in case you want to change default value
            from any model. e.g. change value of og:image to product specific
            images instead of default images
        """
        self.ensure_one()
        title = request.website.name
        if 'name' in self:
            title = '%s | %s' % (self.name, title)

        img_field = 'social_default_image' if request.website.has_social_default_image else 'logo'

        # Default meta for OpenGraph
        default_opengraph = {
            'og:type': 'website',
            'og:title': title,
            'og:site_name': request.website.name,
            'og:url': url_join(request.website.domain or request.httprequest.url_root, self.env['ir.http']._url_for(request.httprequest.path)),
            'og:image': request.website.image_url(request.website, img_field),
        }
        default_twitter = {
            'twitter:card': 'summary_large_image',
        }

        return {
            'default_opengraph': default_opengraph,
            'default_twitter': default_twitter
        }

    def get_website_meta(self):
        """ This method will return final meta information. It will replace
            default values with user's custom value (if user modified it from
            the seo popup of frontend)

            This method is not meant for overridden. To customize meta values
            override `_default_website_meta` method instead of this method. This
            method only replaces user custom values in defaults.
        """
        root_url = request.website.domain or request.httprequest.url_root.strip('/')
        default_meta = self._default_website_meta()
        opengraph_meta, twitter_meta = default_meta['default_opengraph'], default_meta['default_twitter']
        if self.website_meta_title:
            opengraph_meta['og:title'] = self.website_meta_title
        if self.website_meta_description:
            opengraph_meta['og:description'] = self.website_meta_description
        opengraph_meta['og:image'] = url_join(root_url, self.env['ir.http']._url_for(self.website_meta_og_img or opengraph_meta['og:image']))
        return {
            'opengraph_meta': opengraph_meta,
            'twitter_meta': twitter_meta,
            'meta_description': default_meta.get('default_meta_description')
        }


class WebsiteCover_PropertiesMixin(models.AbstractModel):
    _name = 'website.cover_properties.mixin'

    _description = 'Cover Properties Website Mixin'

    cover_properties = fields.Text('Cover Properties', default=lambda s: json_safe.dumps(s._default_cover_properties()))

    def _default_cover_properties(self):
        return {
            "background_color_class": "o_cc3",
            "background-image": "none",
            "opacity": "0.2",
            "resize_class": "o_half_screen_height",
        }

    def _get_background(self, height=None, width=None):
        self.ensure_one()
        properties = json_safe.loads(self.cover_properties)
        img = properties.get('background-image', "none")

        if img.startswith('url(/web/image/'):
            suffix = ""
            if height is not None:
                suffix += "&height=%s" % height
            if width is not None:
                suffix += "&width=%s" % width
            if suffix:
                suffix = '?' not in img and "?%s" % suffix or suffix
                img = img[:-1] + suffix + ')'
        return img

    def write(self, vals):
        if 'cover_properties' not in vals:
            return super().write(vals)

        cover_properties = json_safe.loads(vals['cover_properties'])
        resize_classes = cover_properties.get('resize_class', '').split()
        classes = ['o_half_screen_height', 'o_full_screen_height', 'cover_auto']
        if not set(resize_classes).isdisjoint(classes):
            # Updating cover properties and the given 'resize_class' set is
            # valid, normal write.
            return super().write(vals)

        # If we do not receive a valid resize_class via the cover_properties, we
        # keep the original one (prevents updates on list displays from
        # destroying resize_class).
        copy_vals = dict(vals)
        for item in self:
            old_cover_properties = json_safe.loads(item.cover_properties)
            cover_properties['resize_class'] = old_cover_properties.get('resize_class', classes[0])
            copy_vals['cover_properties'] = json_safe.dumps(cover_properties)
            super(WebsiteCover_PropertiesMixin, item).write(copy_vals)
        return True


class WebsitePageVisibilityOptionsMixin(models.AbstractModel):
    _name = 'website.page_visibility_options.mixin'
    _description = "Website page/record specific visibility options"

    header_visible = fields.Boolean(default=True)
    footer_visible = fields.Boolean(default=True)


class WebsitePageOptionsMixin(models.AbstractModel):
    _name = 'website.page_options.mixin'
    _inherit = ['website.page_visibility_options.mixin']
    _description = "Website page/record specific options"

    header_overlay = fields.Boolean()
    header_color = fields.Char()
    header_text_color = fields.Char()


class WebsiteMultiMixin(models.AbstractModel):
    _name = 'website.multi.mixin'

    _description = 'Multi Website Mixin'

    website_id = fields.Many2one(
        "website",
        string="Website",
        ondelete="restrict",
        help="Restrict to a specific website.",
        index=True,
    )

    def can_access_from_current_website(self, website_id=False):
        can_access = True
        for record in self:
            if (website_id or record.website_id.id) not in (False, request.env['website'].get_current_website().id):
                can_access = False
                continue
        return can_access


class WebsitePublishedMixin(models.AbstractModel):
    _name = 'website.published.mixin'

    _description = 'Website Published Mixin'

    website_published = fields.Boolean('Visible on current website', related='is_published', readonly=False)
    is_published = fields.Boolean('Is Published', copy=False, default=lambda self: self._default_is_published(), index=True)
    publish_on = fields.Datetime(
        "Auto publish on",
        copy=False,
        help="Automatically publish the page on the chosen date and time.",
    )
    published_date = fields.Datetime("Published date", copy=False)
    can_publish = fields.Boolean('Can Publish', compute='_compute_can_publish')
    website_url = fields.Char('Website URL', compute='_compute_website_url', help='The full relative URL to access the document through the website.')
    # The compute dependency (for get_base_url) must be added and get_base_url must be overridden if needed
    website_absolute_url = fields.Char('Website Absolute URL', compute='_compute_website_absolute_url',
                                       help='The full absolute URL to access the document through the website.')

    @api.depends_context('lang')
    def _compute_website_url(self):
        for record in self:
            record.website_url = '#'

    @api.depends('website_url')
    def _compute_website_absolute_url(self):
        self.website_absolute_url = '#'
        for record in self:
            if record.website_url != '#':
                record.website_absolute_url = url_join(record.get_base_url(), record.website_url)

    def _default_is_published(self):
        return False

    def action_unschedule(self):
        self.write({'publish_on': False})

    def _models_generator(self):
        """Yield every stored model defining a ``publish_on`` field.

        Yields:
            odoo.models.BaseModel: Stored models that define a 'publish_on'
                field and expose at least the 'id' and 'is_published' fields.
        """
        field_records = (
            self.env['ir.model.fields']
            .sudo()
            .search([
                ('name', '=', 'publish_on'),
                ('model_id.abstract', '=', False),
                ('store', '=', True),
                ('related', '=', False),
            ])
        )
        seen = set()
        for field in field_records:
            model_name = field.model
            if model_name in seen or model_name not in self.env:
                continue
            model = self.env[model_name]
            if {'id', 'is_published'} <= set(model._fields):
                seen.add(model_name)
                yield model

    def _cron_publish_scheduled_pages(self):
        """Cron helper: publish every scheduled record whose deadline passed."""
        publish_domain = [('publish_on', '!=', False), ('publish_on', '<=', 'now')]
        models_to_process = []
        total_to_process = 0

        for model in self._models_generator():
            model_sudo = model.sudo()
            to_publish_count = model_sudo.search_count(publish_domain)
            if to_publish_count:
                models_to_process.append(model_sudo)
                total_to_process += to_publish_count

        if not total_to_process:
            return

        cron = self.env['ir.cron']
        if not cron._commit_progress(remaining=total_to_process):
            return

        for model in models_to_process:
            pages = model.search(publish_domain, order='publish_on asc, id asc')
            for batch_ids in split_every(100, pages.ids):
                batch = model.browse(batch_ids)
                batch.write({'is_published': True, 'publish_on': False})
                if not cron._commit_progress(processed=len(batch)):
                    return

    def _manage_next_scheduled_action(self):
        scheduled_action = self.env.ref(
            'website.ir_cron_publish_scheduled_pages',
            raise_if_not_found=False,
        )
        if not scheduled_action:
            raise UserError(
                _(
                    'The scheduled action "Website Publish Mixin: Publish scheduled website page" '
                    "has been deleted. Please contact your administrator to restore it or reinstall the website module."
                )
            )

        cron_trigger_env = self.env['ir.cron.trigger'].sudo()
        next_trigger = cron_trigger_env.search(
            [
                ('cron_id', '=', scheduled_action.id),
                ('call_at', '>=', fields.Datetime.now()),
            ],
            order='call_at asc',
            limit=1,
        )
        next_trigger_datetime = next_trigger.call_at if next_trigger else False

        scheduled_datetimes = []
        for model in self._models_generator():
            if model._name == 'website.published.mixin':
                continue
            record = model.sudo().search(
                [('publish_on', '!=', False)],
                order='publish_on asc',
                limit=1,
            )
            if record:
                scheduled_datetimes.append(record.publish_on)

        if not scheduled_datetimes:
            cron_trigger_env.search([
                ('cron_id', '=', scheduled_action.id),
                ('call_at', '>=', fields.Datetime.now()),
            ]).unlink()
            return False

        scheduled_datetimes.sort()
        earliest_datetime = scheduled_datetimes[0]

        if not next_trigger_datetime or earliest_datetime < next_trigger_datetime:
            cron_trigger_env.search([
                ('cron_id', '=', scheduled_action.id),
                ('call_at', '>=', fields.Datetime.now()),
            ]).unlink()
            scheduled_action._trigger(earliest_datetime)

        return True

    def website_publish_button(self):
        self.ensure_one()
        value = not self.website_published
        self.write({'website_published': value, 'publish_on': False})
        return value

    def open_website_url(self):
        return self.env['website'].get_client_action(self.website_url)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        schedule_needed = False
        for record in records:
            if record.is_published and not record.can_publish:
                raise AccessError(self._get_can_publish_error_message())
            if 'active' in record._fields and not record.active and record.is_published:
                record.is_published = False
            if record.publish_on:
                if record.is_published:
                    record.is_published = False
                schedule_needed = True

        records._finalize_publication()

        if schedule_needed:
            self._manage_next_scheduled_action()

        return records

    def write(self, vals):
        publish_keys = {'is_published', 'website_published'}
        if publish_keys & set(vals) and any(not record.can_publish for record in self):
            raise AccessError(self._get_can_publish_error_message())

        # Copy to avoid mutating caller provided dictionary in-place.
        vals = dict(vals)

        if vals.get('is_published') or vals.get('website_published'):
            vals['publish_on'] = False

        if 'active' in vals and vals['active'] is False:
            vals['is_published'] = False
            vals['publish_on'] = False

        if vals.get('publish_on'):
            vals.setdefault('is_published', False)

        previously_published = {record.id: record.is_published for record in self}

        res = super().write(vals)

        if 'publish_on' in vals:
            self._manage_next_scheduled_action()

        if publish_keys & set(vals) and not self.env.context.get('skip_publish_post_process'):
            newly_published = self.filtered(
                lambda record: record.is_published
                and not previously_published.get(record.id)
                and not record.published_date
            )
            newly_published._finalize_publication()

        return res

    def create_and_get_website_url(self, **kwargs):
        return self.create(kwargs).website_url

    def _check_for_action_post_publish(self):
        """Hook for subclasses to add side effects when publishing.

        Returns:
            recordset: mail.message recordset to post or broadcast (empty by
            default).
        """
        return self.env['mail.message']

    def _finalize_publication(self):
        """Handle all post-publication side effects safely and consistently.

        This method centralizes logic that used to be scattered in ORM
        constraints. It ensures cache refresh, chatter notifications, and
        metadata updates are executed once and outside the main write/create
        transaction. This prevents long-lived transactions and stale cache
        issues, while keeping publish behavior identical whether it's triggered
        manually or via cron.
        """

        # Exit early if this call is explicitly skipped by context.
        # (Used to prevent recursion when we write at the end of this method.)
        if self.env.context.get('skip_publish_post_process'):
            return

        # Keep only records that *just became* published, i.e. visible online
        # but not yet stamped with a published_date.
        records = self.filtered(lambda record: record.is_published and not record.published_date)
        if not records:
            return

        # Invalidate the ORM cache for website_published so hooks that read it
        # during this method see the fresh "True" value instead of an old cache.
        records.invalidate_recordset(['website_published'])

        # Prepare containers for all chatter messages and pending notifications.
        messages = self.env['mail.message']
        pending_notifications = []

        # Ask each record if it has a post-publish hook that should run.
        # For example, a blog post may return a chatter message to broadcast.
        for record in records:
            message = record.with_context(force_website_published=True)._check_for_action_post_publish()
            if message:
                messages |= message
                pending_notifications.append(message)

        # ----------------------------------------------------------------------
        # STEP 1: Clear caches before sending notifications
        # ----------------------------------------------------------------------
        if messages:
            # We're about to send notifications, but the ORM might still cache
            # an outdated "who was notified" list. This invalidation ensures
            # that after we post messages, recomputed fields (like
            # notified_partner_ids) correctly reflect the actual recipients.
            messages.invalidate_recordset(['notified_partner_ids'])

        # ----------------------------------------------------------------------
        # STEP 2: Send chatter notifications like the UI would
        # ----------------------------------------------------------------------
        for message in pending_notifications:
            target_sudo = self.env[message.model].browse(message.res_id).sudo()
            message_sudo = message.sudo()
            if not target_sudo:
                continue

            # Rebuild values similar to those passed by the mail composer.
            msg_vals = {
                'partner_ids': message.partner_ids.ids,
                'message_type': message.message_type,
                'subtype_id': message.subtype_id.id,
                'author_id': message.author_id.id,
                'incoming_email_to': message.incoming_email_to,
                'incoming_email_cc': message.incoming_email_cc,
                'outgoing_email_to': message.outgoing_email_to,
            }

            # Compute recipients (followers, partners, etc.)
            recipients = target_sudo._notify_get_recipients(message_sudo, msg_vals=msg_vals)
            if recipients:
                # Mirror the UI path so followers receive the same notifications
                # they would if the message had been posted manually.
                target_sudo._notify_thread(message_sudo, msg_vals=msg_vals, skip_existing=True)

                # We've just sent notifications → clear caches again so
                # message.notified_partner_ids and message.notification_ids
                # reflect the new state right away (who got pinged, which
                # notifications exist).
                message_sudo.invalidate_recordset(
                    ['notified_partner_ids', 'notification_ids']
                )

                # --------------------------------------------------------------
                # STEP 3: Ensure notification rows exist (fallback path)
                # --------------------------------------------------------------
                if not message_sudo.notification_ids:
                    notif_vals = []
                    for recipient in recipients:
                        partner_id = recipient.get('id')
                        if not partner_id:
                            continue
                        notif_vals.append({
                            'author_id': message_sudo.author_id.id,
                            'mail_message_id': message_sudo.id,
                            'notification_status': 'sent',
                            'notification_type': recipient.get('notif') or 'inbox',
                            'res_partner_id': partner_id,
                        })
                    if notif_vals:
                        # Create missing mail.notification records manually so
                        # that automated publishes leave the same audit trail as
                        # UI posts.
                        self.env['mail.notification'].sudo().create(notif_vals)

                        # Again, refresh caches for message relations so that
                        # chatter views show the up-to-date "who was notified"
                        # list.
                        message_sudo.invalidate_recordset(
                            ['notified_partner_ids', 'notification_ids']
                        )

        # ----------------------------------------------------------------------
        # STEP 4: Stamp publish date and clear any publish_on schedule
        # ----------------------------------------------------------------------
        # The context flag prevents re-entering this method during this write.
        records.with_context(skip_publish_post_process=True).write({
            'published_date': fields.Datetime.now(),
            'publish_on': False,
        })

    @api.depends_context('uid')
    def _compute_can_publish(self):
        """ This method can be overridden if you need more complex rights
        management than just write access to the model.
        The publish widget will be hidden and the user won't be able to change
        the 'website_published' value if this method sets can_publish False """
        for record in self:
            try:
                self.env['website'].get_current_website()._check_user_can_modify(record)
                record.can_publish = True
            except AccessError:
                record.can_publish = False

    @api.model
    def _get_can_publish_error_message(self):
        """ Override this method to customize the error message shown when the user doesn't
        have the rights to publish/unpublish. """
        return _("You do not have the rights to publish/unpublish")


class WebsitePublishedMultiMixin(WebsitePublishedMixin):
    _name = 'website.published.multi.mixin'
    _inherit = ['website.published.mixin', 'website.multi.mixin']
    _description = 'Multi Website Published Mixin'

    website_published = fields.Boolean(compute='_compute_website_published',
                                       inverse='_inverse_website_published',
                                       search='_search_website_published',
                                       related=False, readonly=False)

    @api.depends('is_published', 'website_id')
    @api.depends_context('website_id')
    def _compute_website_published(self):
        current_website_id = self.env.context.get('website_id')
        for record in self:
            if current_website_id:
                record.website_published = record.is_published and (not record.website_id or record.website_id.id == current_website_id)
            else:
                record.website_published = record.is_published

    def _inverse_website_published(self):
        for record in self:
            record.is_published = record.website_published

    def _search_website_published(self, operator, value):
        if operator != 'in':
            return NotImplemented
        assert list(value) == [True]

        current_website_id = self.env.context.get('website_id')
        is_published = Domain('is_published', '=', True)
        if current_website_id:
            on_current_website = self.env['website'].browse(current_website_id).website_domain()
            return is_published & on_current_website
        else:  # should be in the backend, return things that are published anywhere
            return is_published

    def open_website_url(self):
        website_id = False
        if self.website_id:
            website_id = self.website_id.id
            if self.website_id.domain:
                client_action_url = self.env['website'].get_client_action_url(self.website_url)
                client_action_url = f'{client_action_url}&website_id={website_id}'
                return {
                    'type': 'ir.actions.act_url',
                    'url': url_join(self.website_id.domain, client_action_url),
                    'target': 'self',
                }
        return self.env['website'].get_client_action(self.website_url, False, website_id)


class WebsiteSearchableMixin(models.AbstractModel):
    """Mixin to be inherited by all models that need to searchable through website"""
    _name = 'website.searchable.mixin'
    _description = 'Website Searchable Mixin'

    @api.model
    def _search_build_domain(self, domain_list, search, fields, extra=None):
        """
        Builds a search domain AND-combining a base domain with partial matches of each term in
        the search expression in any of the fields.

        :param domain_list: base domain list combined in the search expression
        :param search: search expression string
        :param fields: list of field names to match the terms of the search expression with
        :param extra: function that returns an additional subdomain for a search term

        :return: domain limited to the matches of the search expression
        """
        domain = Domain.AND(domain_list)
        if search:
            for search_term in search.split():
                subdomains = [Domain(field, 'ilike', escape_psql(search_term)) for field in fields]
                if extra:
                    subdomains.append(extra(self.env, search_term))
                domain &= Domain.OR(subdomains)
        return domain

    @api.model
    def _search_get_detail(self, website, order, options):
        """
        Returns indications on how to perform the searches

        :param website: website within which the search is done
        :param order: order in which the results are to be returned
        :param options: search options

        :return: search detail as expected in elements of the result of website._search_get_details()
            These elements contain the following fields:
            - model: name of the searched model
            - base_domain: list of domains within which to perform the search
            - search_fields: fields within which the search term must be found
            - fetch_fields: fields from which data must be fetched
            - mapping: mapping from the results towards the structure used in rendering templates.
                The mapping is a dict that associates the rendering name of each field
                to a dict containing the 'name' of the field in the results list and the 'type'
                that must be used for rendering the value
            - icon: name of the icon to use if there is no image

        This method must be implemented by all models that inherit this mixin.
        """
        raise NotImplementedError()

    @api.model
    def _search_fetch(self, search_detail, search, limit, order):
        fields = search_detail['search_fields']
        base_domain = search_detail['base_domain']
        domain = self._search_build_domain(base_domain, search, fields, search_detail.get('search_extra'))
        model = self.sudo() if search_detail.get('requires_sudo') else self
        results = model.search(
            domain,
            limit=limit,
            order=search_detail.get('order', order)
        )
        count = model.search_count(domain) if limit and limit == len(results) else len(results)
        return results, count

    def _search_render_results(self, fetch_fields, mapping, icon, limit):
        results_data = self.read(fetch_fields)[:limit]
        for result in results_data:
            result['_fa'] = icon
            result['_mapping'] = mapping
        html_fields = [config['name'] for config in mapping.values() if config.get('html')]
        if html_fields:
            for data in results_data:
                for html_field in html_fields:
                    if data[html_field]:
                        if html_field == 'arch':
                            # Undo second escape of text nodes from wywsiwyg.js _getEscapedElement.
                            data[html_field] = re.sub(r'&amp;(?=\w+;)', '&', data[html_field])
                        text = text_from_html(data[html_field], True)
                        data[html_field] = text
        return results_data
