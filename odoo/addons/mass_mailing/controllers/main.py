# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import urllib.parse
import werkzeug

from datetime import timedelta
from markupsafe import Markup, escape
from lxml import etree
from werkzeug.exceptions import BadRequest, NotFound, Unauthorized

from odoo import _, fields, http, tools
from odoo.http import request, Response
from odoo.tools import consteq


class MassMailController(http.Controller):

    def _check_mailing_email_token(self, mailing_id, document_id, email, hash_token,
                                   required_mailing_id=False):
        """ Return the mailing based on given credentials, sudo-ed. Raises if
        there is an issue fetching it.

        Specific use case
          * hash_token is always required for public users, no generic page is
            available for them;
          * hash_token is not required for generic page for logged user, aka
            if no mailing_id is given;
          * hash_token is not required for mailing specific page if the user
            is a mailing user;
          * hash_token is not required for generic page for logged user, aka
            if no mailing_id is given and if mailing_id is not required;
          * hash_token always requires the triplet mailing_id, email and
            document_id, as it indicates it comes from a mailing email and
            is used when comparing hashes;
        """
        if not hash_token:
            if request.env.user._is_public():
                raise BadRequest()
            if mailing_id and not request.env.user.has_group('mass_mailing.group_mass_mailing_user'):
                raise BadRequest()
        if hash_token and (not mailing_id or not email or not document_id):
            raise BadRequest()
        if mailing_id:
            mailing_sudo = request.env['mailing.mailing'].sudo().browse(mailing_id)
            if not mailing_sudo.exists():
                raise NotFound()
            if hash_token and not consteq(mailing_sudo._generate_mailing_recipient_token(document_id, email), hash_token):
                raise Unauthorized()
        else:
            if required_mailing_id:
                raise BadRequest()
            mailing_sudo = request.env['mailing.mailing'].sudo()
        return mailing_sudo

    def _fetch_blocklist_record(self, email):
        if not email or not tools.email_normalize(email):
            return None
        return request.env['mail.blacklist'].sudo().with_context(
            active_test=False
        ).search(
            [('email', '=', tools.email_normalize(email))]
        )

    def _fetch_contacts(self, email):
        if not email or not tools.email_normalize(email):
            return request.env['mailing.contact']
        return request.env['mailing.contact'].sudo().search(
            [('email_normalized', '=', tools.email_normalize(email))]
        )

    def _fetch_subscription_optouts(self):
        return request.env['mailing.subscription.optout'].sudo().search([])

    def _fetch_user_information(self, email, hash_token):
        if hash_token or request.env.user._is_public():
            return email, hash_token
        return request.env.user.email_normalized, None

    # ------------------------------------------------------------
    # SUBSCRIPTION MANAGEMENT
    # ------------------------------------------------------------

    @http.route('/mailing/my', type='http', website=True, auth='user')
    def mailing_my(self):
        email, _hash_token = self._fetch_user_information(None, None)
        if not email:
            raise Unauthorized()

        render_values = self._prepare_mailing_subscription_values(
            request.env['mailing.mailing'], False, email, None
        )
        render_values.update(feedback_enabled=False)
        return request.render(
            'mass_mailing.page_mailing_unsubscribe',
            render_values
        )

    # csrf is disabled here because it will be called by the MUA with unpredictable session at that time
    @http.route(['/mailing/<int:mailing_id>/unsubscribe_oneclick'], type='http', website=True, auth='public',
                methods=["POST"], csrf=False)
    def mailing_unsubscribe_oneclick(self, mailing_id, document_id=None, email=None, hash_token=None, **post):
        self.mailing_unsubscribe(mailing_id, document_id=document_id, email=email, hash_token=hash_token, **post)
        return Response(status=200)

    @http.route('/mailing/<int:mailing_id>/confirm_unsubscribe', type='http', website=True, auth='public')
    def mailing_confirm_unsubscribe(self, mailing_id, document_id=None, email=None, hash_token=None):
        mailing = request.env['mailing.mailing'].sudo().browse(mailing_id)
        # check that mailing exists/has access
        email_found, hash_token_found = self._fetch_user_information(email, hash_token)
        try:
            self._check_mailing_email_token(
                mailing_id, document_id, email_found, hash_token_found,
                required_mailing_id=True
            )
        except NotFound as e:  # avoid leaking ID existence
            raise Unauthorized() from e

        unsubscribed_str = _('Are you sure you want to unsubscribe from our mailing list?')
        # Display list name if list is public
        if mailing.mailing_model_real == 'mailing.contact':
            unsubscribed_lists = ', '.join(mailing_list.name for mailing_list in mailing.contact_list_ids if mailing_list.is_public)
            if unsubscribed_lists:
                unsubscribed_str = _(
                    'Are you sure you want to unsubscribe from the mailing list "%(unsubscribed_lists)s"?',
                    unsubscribed_lists=unsubscribed_lists
                )

        template = etree.fromstring("""
            <t t-call="mass_mailing.layout">
                <div class="container o_unsubscribe_form">
                    <div class="row">
                        <div class="col-lg-6 offset-lg-3 mt-4">
                            <div id="info_state"  class="alert alert-success">
                                <div class="text-center">
                                    <form action="/mailing/confirm_unsubscribe" method="POST">
                                        <input type="hidden" name="csrf_token" t-att-value="request.csrf_token()"/>
                                        <input type="hidden" name="mailing_id" t-att-value="mailing_id"/>
                                        <input type="hidden" name="document_id" t-att-value="document_id"/>
                                        <input type="hidden" name="email" t-att-value="email"/>
                                        <input type="hidden" name="hash_token" t-att-value="hash_token"/>
                                        <p t-out="unsubscribed_str"/>
                                        <button type="submit" class="btn btn-primary" t-out="unsubscribe_btn"/>
                                    </form>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </t>
        """)
        return request.env['ir.qweb']._render(template, {
            'main_object': mailing,
            'mailing_id': mailing_id,
            'document_id': document_id,
            'email': email,
            'hash_token': hash_token,
            'unsubscribed_str': unsubscribed_str,
            'unsubscribe_btn': _("Unsubscribe"),
        })

    # POST method
    # kept for backwards compatibility, must eventually be merged with mailing/<mailing_id>/unsubscribe
    @http.route('/mailing/confirm_unsubscribe', type='http', website=True, auth='public', methods=['POST'])
    def mailing_confirm_unsubscribe_post(self, mailing_id, document_id=None, email=None, hash_token=None):
        # Unsubscribe user
        email_found, hash_token_found = self._fetch_user_information(email, hash_token)
        try:
            mailing_sudo = self._check_mailing_email_token(
                int(mailing_id), document_id, email_found, hash_token_found,
                required_mailing_id=True
            )
        except NotFound as e:  # fails if mailing doesn't exist or token is wrong
            raise Unauthorized() from e

        if mailing_sudo.mailing_on_mailing_list:
            self._mailing_unsubscribe_from_list(mailing_sudo, document_id, email_found, hash_token_found)
        else:
            self._mailing_unsubscribe_from_document(mailing_sudo, document_id, email_found, hash_token_found)

        url_params = urllib.parse.urlencode({
            'email': email,
            'document_id': document_id,
            'hash_token': hash_token,
        })
        settings_url = f'/mailing/{int(mailing_id)}/unsubscribe?{url_params}'
        template = etree.fromstring("""
            <t t-call="mass_mailing.layout">
                <div class="container o_unsubscribe_form">
                    <div class="row">
                        <div class="col-lg-6 offset-lg-3 mt-4">
                            <div id="info_state"  class="alert alert-success">
                                <div class="text-center">
                                    <p t-out="success_str"/>
                                    <a t-att-href="settings_url" class="btn btn-primary" t-out="manage_btn"/>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </t>
        """)
        return request.env['ir.qweb']._render(template, {
            'main_object': request.env['mailing.mailing'].browse(int(mailing_id)),
            'settings_url': settings_url,
            'success_str': _('Successfully unsubscribed!'),
            'manage_btn': _('Manage Subscriptions'),
        })

    # todo: merge this route with /mail/mailing/confirm_unsubscribe on next minor version
    @http.route(['/mailing/<int:mailing_id>/unsubscribe'], type='http', website=True, auth='public')
    def mailing_unsubscribe(self, mailing_id, document_id=None, email=None, hash_token=None):
        email_found, hash_token_found = self._fetch_user_information(email, hash_token)
        try:
            mailing_sudo = self._check_mailing_email_token(
                mailing_id, document_id, email_found, hash_token_found,
                required_mailing_id=True
            )
        except NotFound as e:  # avoid leaking ID existence
            raise Unauthorized() from e

        if mailing_sudo.mailing_on_mailing_list:
            return self._mailing_unsubscribe_from_list(mailing_sudo, document_id, email_found, hash_token_found)
        return self._mailing_unsubscribe_from_document(mailing_sudo, document_id, email_found, hash_token_found)

    def _mailing_unsubscribe_from_list(self, mailing, document_id, email, hash_token):
        # Unsubscribe directly + Let the user choose their subscriptions

        mailing.contact_list_ids._update_subscription_from_email(email, opt_out=True)
        # compute name of unsubscribed list: hide non public lists
        if all(not mlist.is_public for mlist in mailing.contact_list_ids):
            lists_unsubscribed_name = _('You are no longer part of our mailing list(s).')
        elif len(mailing.contact_list_ids) == 1:
            lists_unsubscribed_name = _('You are no longer part of the %(mailing_name)s mailing list.',
                                        mailing_name=mailing.contact_list_ids.name)
        else:
            lists_unsubscribed_name = _(
                'You are no longer part of the %(mailing_names)s mailing list.',
                mailing_names=', '.join(mlist.name for mlist in mailing.contact_list_ids if mlist.is_public)
            )

        return request.render(
            'mass_mailing.page_mailing_unsubscribe',
            dict(
                self._prepare_mailing_subscription_values(
                    mailing, document_id, email, hash_token
                ),
                last_action='subscription_updated',
                unsubscribed_name=lists_unsubscribed_name,
            )
        )

    def _mailing_unsubscribe_from_document(self, mailing, document_id, email, hash_token):
        if document_id:
            message = Markup(_(
                'Blocklist request from unsubscribe link of mailing %(mailing_link)s (document %(record_link)s)',
                **self._format_bl_request(mailing, document_id)
            ))
        else:
            message = Markup(_(
                'Blocklist request from unsubscribe link of mailing %(mailing_link)s (direct link usage)',
                **self._format_bl_request(mailing, document_id)
            ))
        _blocklist_rec = request.env['mail.blacklist'].sudo()._add(email, message=Markup('<p>%s</p>') % message)

        return request.render(
            'mass_mailing.page_mailing_unsubscribe',
            dict(
                self._prepare_mailing_subscription_values(
                    mailing, document_id, email, hash_token
                ),
                last_action='blocklist_add',
                unsubscribed_name=_('You are no longer part of our services and will not be contacted again.'),
            )
        )

    def _prepare_mailing_subscription_values(self, mailing, document_id, email, hash_token):
        """ Prepare common values used in various subscription management or
        blocklist flows done in portal. """
        mail_blocklist = self._fetch_blocklist_record(email)
        email_normalized = tools.email_normalize(email)

        # fetch optout/blacklist reasons
        opt_out_reasons = self._fetch_subscription_optouts()

        # as there may be several contacts / email -> consider any opt-in overrides
        # opt-out
        contacts = self._fetch_contacts(email)
        lists_optin = contacts.subscription_ids.filtered(
            lambda sub: not sub.opt_out
        ).list_id.filtered('active')
        lists_optout = contacts.subscription_ids.filtered(
            lambda sub: sub.opt_out and sub.list_id not in lists_optin
        ).list_id.filtered('active')
        lists_public = request.env['mailing.list'].sudo().search(
            [('is_public', '=', True),
             ('id', 'not in', (lists_optin + lists_optout).ids)
            ],
            limit=10,
            order='create_date DESC, id DESC',
        )

        return {
            # customer
            'document_id': document_id,
            'email': email,
            'email_valid': bool(email_normalized),
            'hash_token': hash_token,
            'mailing_id': mailing.id,
            'res_id': document_id,
            # feedback
            'feedback_enabled': True,
            'feedback_readonly': False,
            'opt_out_reasons': opt_out_reasons,
            # blocklist
            'blocklist_enabled': bool(
                request.env['ir.config_parameter'].sudo().get_param(
                    'mass_mailing.show_blacklist_buttons',
                    default=True,
                )
            ),
            'blocklist_possible': mail_blocklist is not None,
            'is_blocklisted': mail_blocklist.active if mail_blocklist else False,
            # mailing lists
            'contacts': contacts,
            'lists_contacts': contacts.subscription_ids.list_id.filtered('active'),
            'lists_optin': lists_optin,
            'lists_optout': lists_optout,
            'lists_public': lists_public,
        }

    @http.route('/mailing/list/update', type='json', auth='public', csrf=True)
    def mailing_update_list_subscription(self, mailing_id=None, document_id=None,
                                         email=None, hash_token=None,
                                         lists_optin_ids=None, **post):
        email_found, hash_token_found = self._fetch_user_information(email, hash_token)
        try:
            _mailing_sudo = self._check_mailing_email_token(
                mailing_id, document_id, email_found, hash_token_found,
                required_mailing_id=False
            )
        except BadRequest:
            return 'error'
        except (NotFound, Unauthorized):
            return 'unauthorized'

        contacts = self._fetch_contacts(email_found)
        lists_optin = request.env['mailing.list'].sudo().browse(lists_optin_ids or []).exists()
        # opt-out all not chosen lists
        lists_to_optout = contacts.subscription_ids.filtered(
            lambda sub: not sub.opt_out and sub.list_id not in lists_optin
        ).list_id
        # opt-in in either already member, either public (to avoid trying to opt-in
        # in private lists)
        lists_to_optin = lists_optin.filtered(
            lambda mlist: mlist.is_public or mlist in contacts.list_ids
        )
        lists_to_optout._update_subscription_from_email(email_found, opt_out=True)
        lists_to_optin._update_subscription_from_email(email_found, opt_out=False)

        return len(lists_to_optout)

    @http.route('/mailing/feedback', type='json', auth='public', csrf=True)
    def mailing_send_feedback(self, mailing_id=None, document_id=None,
                              email=None, hash_token=None,
                              last_action=None,
                              opt_out_reason_id=False, feedback=None,
                              **post):
        """ Feedback can be given after some actions, notably after opt-outing
        from mailing lists or adding an email in the blocklist.

        This controller tries to write the customer feedback in the most relevant
        record. Feedback consists in two parts, the opt-out reason (based on data
        in 'mailing.subscription.optout' model) and the feedback itself (which
        is triggered by the optout reason 'is_feedback' fields).
        """
        email_found, hash_token_found = self._fetch_user_information(email, hash_token)
        try:
            mailing_sudo = self._check_mailing_email_token(
                mailing_id, document_id, email_found, hash_token_found,
                required_mailing_id=False,
            )
        except BadRequest:
            return 'error'
        except (NotFound, Unauthorized):
            return 'unauthorized'

        if not opt_out_reason_id:
            return 'error'
        feedback = feedback.strip() if feedback else ''
        message = ''
        if feedback:
            if not request.env.user._is_public():
                author_name = f'{request.env.user.name} ({email_found})'
            else:
                author_name = email_found
            message = Markup("<p>%s<br />%s</p>") % (
                _('Feedback from %(author_name)s', author_name=author_name),
                feedback
            )

        # blocklist addition: opt-out and feedback linked to the mail.blacklist records
        if last_action == 'blocklist_add':
            mail_blocklist = self._fetch_blocklist_record(email)
            if mail_blocklist:
                if message:
                    mail_blocklist._track_set_log_message(message)
                mail_blocklist.opt_out_reason_id = opt_out_reason_id

        # opt-outed from mailing lists (either from a mailing or directly from 'my')
        # -> in that case, update recently-updated subscription records and log on
        # contacts
        documents_for_post = []
        if (last_action in {'subscription_updated', 'subscription_updated_optout'} or
            (not last_action and (not mailing_sudo or mailing_sudo.mailing_on_mailing_list))):
            contacts = self._fetch_contacts(email_found)
            contacts.subscription_ids.filtered(
                lambda sub: sub.opt_out and sub.opt_out_datetime >= (fields.Datetime.now() - timedelta(minutes=10))
            ).opt_out_reason_id = opt_out_reason_id
            if message:
                documents_for_post = contacts
        # feedback coming from a mailing, without additional context information: log
        elif mailing_sudo and message:
            documents_for_post = request.env[mailing_sudo.mailing_model_real].sudo().search(
                [('id', '=', document_id)
            ])

        for document_sudo in documents_for_post:
            document_sudo.message_post(body=message)

        return True

    @http.route(['/unsubscribe_from_list'], type='http', website=True, multilang=False, auth='public', sitemap=False)
    def mailing_unsubscribe_placeholder_link(self, **post):
        """Dummy route so placeholder is not prefixed by language, MUST have multilang=False"""
        return request.redirect('/mailing/my', code=301, local=True)

    # ------------------------------------------------------------
    # TRACKING
    # ------------------------------------------------------------

    @http.route('/mail/track/<int:mail_id>/<string:token>/blank.gif', type='http', auth='public')
    def track_mail_open(self, mail_id, token, **post):
        """ Email tracking. """
        expected_token = request.env['mail.mail']._generate_mail_recipient_token(mail_id)
        if not consteq(token, expected_token):
            raise Unauthorized()

        request.env['mailing.trace'].sudo().set_opened(domain=[('mail_mail_id_int', 'in', [mail_id])])
        response = Response()
        response.mimetype = 'image/gif'
        response.data = base64.b64decode(b'R0lGODlhAQABAIAAANvf7wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==')

        return response

    @http.route('/r/<string:code>/m/<int:mailing_trace_id>', type='http', auth="public")
    def full_url_redirect(self, code, mailing_trace_id, **post):
        request.env['link.tracker.click'].sudo().add_click(
            code,
            ip=request.httprequest.remote_addr,
            country_code=request.geoip.country_code,
            mailing_trace_id=mailing_trace_id
        )
        redirect_url = request.env['link.tracker'].get_url_from_code(code)
        if not redirect_url:
            raise NotFound()
        return request.redirect(redirect_url, code=301, local=False)

    # ------------------------------------------------------------
    # MAILING MANAGEMENT
    # ------------------------------------------------------------

    @http.route('/mailing/report/unsubscribe', type='http', website=True, auth='public')
    def mailing_report_deactivate(self, token, user_id):
        if not token or not user_id:
            raise BadRequest()
        user = request.env['res.users'].sudo().browse(int(user_id)).exists()
        if not user or not user.has_group('mass_mailing.group_mass_mailing_user') or \
           not consteq(token, request.env['mailing.mailing']._generate_mailing_report_token(user.id)):
            raise Unauthorized()

        request.env['ir.config_parameter'].sudo().set_param('mass_mailing.mass_mailing_reports', False)
        render_vals = {}
        if user.has_group('base.group_system'):
            render_vals = {'menu_id': request.env.ref('mass_mailing.menu_mass_mailing_global_settings').id}
        return request.render('mass_mailing.mailing_report_deactivated', render_vals)

    @http.route(['/mailing/<int:mailing_id>/view'], type='http', website=True, auth='public')
    def mailing_view_in_browser(self, mailing_id, email=None, document_id=None, hash_token=None, **kwargs):
        # backward compatibility: temporary for mailings sent before migation to 17
        document_id = document_id or kwargs.get('res_id')
        hash_token = hash_token or kwargs.get('token')
        try:
            mailing_sudo = self._check_mailing_email_token(
                mailing_id, document_id, email, hash_token,
                required_mailing_id=True,
            )
        except NotFound as e:
            raise Unauthorized() from e

        # do not force lang, will simply use user context
        document_id = int(document_id) if document_id and document_id.isdigit() else 0
        html_markupsafe = mailing_sudo._render_field(
            'body_html',
            [document_id],
            compute_lang=False,
            options={'post_process': False}
        )[document_id]
        # Update generic URLs (without parameters) to final ones
        if document_id:
            html_markupsafe = html_markupsafe.replace(
                '/unsubscribe_from_list',
                mailing_sudo._get_unsubscribe_url(email, document_id)
            )
        else:  # when manually trying a /view on a mailing, not through email link
            html_markupsafe = html_markupsafe.replace(
                '/unsubscribe_from_list',
                werkzeug.urls.url_join(
                    mailing_sudo.get_base_url(),
                    f'/mailing/{mailing_sudo.id}/unsubscribe',
                )
            )

        return request.render(
            'mass_mailing.mailing_view',
            {
                'body': html_markupsafe,
            },
        )

    # ------------------------------------------------------------
    # BLACKLIST
    # ------------------------------------------------------------

    @http.route('/mailing/blocklist/add', type='json', auth='public')
    def mail_blocklist_add(self, mailing_id=None, document_id=None,
                           email=None, hash_token=None):
        email_found, hash_token_found = self._fetch_user_information(email, hash_token)
        try:
            mailing_sudo = self._check_mailing_email_token(
                mailing_id, document_id, email_found, hash_token_found,
                required_mailing_id=False,
            )
        except BadRequest:
            return 'error'
        except (NotFound, Unauthorized):
            return 'unauthorized'

        if mailing_sudo:
            message = Markup(
                _(
                    'Blocklist request from portal of mailing %(mailing_link)s (document %(record_link)s)',
                    **self._format_bl_request(mailing_sudo, document_id)
                )
            )
        else:
            message = Markup('<p>%s</p>') % _('Blocklist request from portal')

        _blocklist_rec = request.env['mail.blacklist'].sudo()._add(email_found, message=message)
        return True

    @http.route('/mailing/blocklist/remove', type='json', auth='public')
    def mail_blocklist_remove(self, mailing_id=None, document_id=None,
                              email=None, hash_token=None):
        email_found, hash_token_found = self._fetch_user_information(email, hash_token)
        try:
            mailing_sudo = self._check_mailing_email_token(
                mailing_id, document_id, email_found, hash_token_found,
                required_mailing_id=False,
            )
        except BadRequest:
            return 'error'
        except (NotFound, Unauthorized):
            return 'unauthorized'

        if mailing_sudo and document_id:
            message = Markup(
                _(
                    'Blocklist removal request from portal of mailing %(mailing_link)s (document %(record_link)s)',
                    **self._format_bl_request(mailing_sudo, document_id)
                )
            )
        else:
            message = Markup('<p>%s</p>') % _('Blocklist removal request from portal')

        _blocklist_rec = request.env['mail.blacklist'].sudo()._remove(email_found, message=message)
        return True

    def _format_bl_request(self, mailing, document_id):
        mailing_model_name = request.env['ir.model']._get(mailing.mailing_model_real).display_name
        return {
            'mailing_link': Markup(f'<a href="#" data-oe-model="mailing.mailing" data-oe-id="{mailing.id}">{escape(mailing.subject)}</a>'),
            'record_link': Markup(
                f'<a href="#" data-oe-model="{escape(mailing.mailing_model_real)}" data-oe-id="{int(document_id)}">{escape(mailing_model_name)}</a>'
            ) if document_id else '',
        }

    # ------------------------------------------------------------
    # PREVIEW
    # ------------------------------------------------------------

    @http.route('/mailing/mobile/preview', methods=['GET'], type='http', auth='user', website=True)
    def mass_mailing_preview_mobile_content(self):
        return request.render("mass_mailing.preview_content_mobile", {})
