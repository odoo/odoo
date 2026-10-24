# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.addons.base.models.ir_qweb_fields import nl2br_enclose
from odoo.addons.website.controllers.form import WebsiteForm
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.tools.translate import _

# Standard signup fields and values derived from them are handled by
# `auth_signup`. Other fields posted to `/web/signup` are added through the
# website editor.
SIGNUP_FORM_INPUTS = {
    'confirm_password', 'csrf_token', 'db', 'email', 'login', 'name', 'password', 'redirect',
    'token',
}


class WebsiteAuthSignupHome(AuthSignupHome):
    """ Handle the fields added on the signup form through the website editor.

    Those fields are posted along with the standard signup form: the ones
    matching a `res.partner` field allowed in the form builder are written on
    the partner created by the signup, the other ones are logged in its chatter.
    """

    @http.route()
    def web_auth_signup(self, *args, **kw):
        request.update_context(website_signup_extra_fields=True)
        return super().web_auth_signup(*args, **kw)

    def do_signup(self, qcontext, do_login=True):
        # Extract before the signup, so that an invalid value does not create
        # a user that would be missing the values of its extra fields.
        data = self._extract_signup_extra_data()
        super().do_signup(qcontext, do_login=do_login)
        if data:
            self._apply_signup_extra_data(qcontext.get('login'), data)

    def _extract_signup_extra_data(self):
        """ Extract the values posted by the extra fields of the signup form.

        The values are extracted as for any other website form, so that only the
        fields opted in the form builder (see `formbuilder_whitelist`) can be
        written on the partner.

        :return: the data extracted from `WebsiteForm.extract_data`, empty
            if the form has no extra field
        :rtype: dict
        """
        if not self.env.context.get('website_signup_extra_fields'):
            return {}
        # The form is submitted by the browser, not by the form interaction
        # (`form.js`), so the values are prepared the same way: `request.params`
        # only keeps the first value of the inputs sharing a name (e.g. multiple
        # checkboxes), which are joined, and multiple files are indexed.
        httprequest = request.httprequest
        values = {
            name: ",".join(field_values)
            for name, field_values in httprequest.form.lists()
            if name not in SIGNUP_FORM_INPUTS
        }
        for name, files in httprequest.files.lists():
            for index, file in enumerate(files):
                values[f"{name}[0][{index}]"] = file
        if not values:
            return {}
        model_sudo = self.env['ir.model'].sudo()._get('res.partner')
        try:
            return WebsiteForm().extract_data(model_sudo, values)
        except ValidationError as e:
            raise UserError(_(
                "Invalid value for the field(s): %(fields)s",
                fields=", ".join(e.args[0]),
            )) from e

    def _apply_signup_extra_data(self, login, data):
        """ Write the extracted data on the `res.partner` model of the user
        created by the signup.

        :param str login: login of the signed up user
        :param dict data: data returned by :meth:`_extract_signup_extra_data`
        """
        User = self.env['res.users'].sudo()
        partner = User.search(
            User._get_login_domain(login), order=User._get_login_order(), limit=1,
        ).partner_id
        if not partner:
            return
        if data['record']:
            partner.write(data['record'])
        if data['custom']:
            partner._message_log(
                body=nl2br_enclose(
                    "%s\n___________\n\n%s" % (_("Other Information:"), data['custom']), 'p',
                ),
                message_type='comment',
            )
        if data['attachments']:
            WebsiteForm().insert_attachment(
                self.env['ir.model'].sudo()._get('res.partner'), partner.id, data['attachments'],
            )
