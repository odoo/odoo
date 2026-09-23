from werkzeug.exceptions import NotFound

from odoo.http import request


def downgrade_to_public_user():
    public_user = request.env.ref("base.public_user")
    request.session.uid = None
    request.update_env(user=public_user)
    request.cookies = {}


def force_guest_env(guest_token, raise_if_not_found=True):
    downgrade_to_public_user()
    guest = request.env["mail.guest"]._get_guest_from_token(guest_token)
    if guest:
        request.update_context(guest=guest)
    elif raise_if_not_found:
        raise NotFound
