# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request
from werkzeug.exceptions import NotFound

def downgrade_to_public_user():
    """Replace the request user by the public one. All the cookies are removed
    in order to ensure that the no user-specific data is kept in the request."""
    public_user = request.env.ref("base.public_user")
    request.update_env(user=public_user)
    request.httprequest.cookies = {}


def force_guest_env(guest_token):
    """Retrieve the guest from the given token and add it to the context.
    The request user is then replaced by the public one.

    :param str guest_token:
    :raise NotFound: if the guest cannot be found from the token
    """
    guest = request.env["mail.guest"]._get_guest_from_token(guest_token)
    if not guest:
        raise NotFound()
    request.update_context(guest=guest)
    downgrade_to_public_user()
