# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from hashlib import sha1

from odoo.http import Controller, request, route, Response, local_redirect
from odoo import tools

class Avatar(Controller):
    @route([
        '/web/avatar/<string:res_model>/<int:user_id>',
        '/web/avatar/<string:res_model>/<int:user_id>/<string:field>'
    ], auth='public', methods=['GET'])
    def get_avatar(self, res_model='res.users', user_id=1, field='image_128', **kwargs):
        """
        Returns a custom avatar based on the user's data
            res_model: corresponding model
            user_id: user id
            field: image field
        """
        if res_model not in ['res.users', 'res.partner', 'hr.employee', 'hr.employee.public']:
            return local_redirect(f'/web/image?model={res_model}&id={user_id}&field={field}')
        user = request.env[res_model].sudo().browse(user_id).exists()
        if not user:
            return request.not_found()
        if user[field]:
            return local_redirect(f'/web/image?model={res_model}&id={user_id}&field={field}')
        avatar = _generate_avatar_svg(user.name)
        return Response(avatar, mimetype='image/svg+xml')

def _encode_name(name):
    return sha1(name.encode('utf-8'))

def _generate_avatar_svg(name):
    base = _encode_name(name)
    initials = tools.html_escape(_generate_initials(name))
    bgcolor = tools.html_escape(_generate_bgcolor(base))
    if initials:
        return (
            "<?xml version='1.0' encoding='UTF-8' ?>"
            "<svg height='180' width='180' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'>"
            f"<rect fill='{bgcolor}' height='180' width='180'/>"
            f"<text fill='#ffffff' font-size='96' text-anchor='middle' x='90' y='125' font-family='sans-serif'>{initials}</text>"
            "</svg>"
        )
    else:
        return _generate_default_avatar()

def _generate_default_avatar(bgcolor='hsl(230, 0%, 90%)'):
    return (
        "<?xml version='1.0' encoding='UTF-8' ?>"
        "<svg height='180' width='180' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'>"
        f"<rect fill='{tools.html_escape(bgcolor)}' height='180' width='180'/>"
        "<text fill='#ffffff' font-size='120' text-anchor='middle' x='90' y='155' font-family='sans-serif'>&#x1F464;</text>"
        "</svg>"
    )

def _generate_initials(name):
    return name[0].upper() if name else ''

def _generate_bgcolor(name):
    if name:
        base = name.hexdigest()[0:6]
        hue = _get_hue(base[0:2])
        sat = _get_sat(base[2:4])
        lig = _get_lig(base[4:6])
        return f'hsl({hue}, {sat}%, {lig}%)'
    return 'hsl(180, 50%, 50%)'

def _get_hue(value):
    hue_max = 360
    hue_dec = int(value, 16)
    return hue_dec * hue_max / 255

def _get_sat(value):
    sat_min = 40
    sat_max = 70
    sat_dec = int(value, 16)
    return sat_dec * ((sat_max - sat_min) / 255) + sat_min

def _get_lig(value):
    return 45
