# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from . import models
from . import tools
from . import wizard
from . import controllers

def _mail_post_init(env):
    env['mail.alias.domain']._migrate_icp_to_domain()
    admin_lang = env.ref("base.partner_admin").lang
    translate_env = env(context=dict(env.context, lang=admin_lang))
    env.ref("mail.channel_all_employees").write({
        "name": translate_env._("General"),
        "description": translate_env._(
            "A place to connect and exchange news with colleagues across the company.",
        ),
    })
    env.ref("mail.channel_admin").write({
        "name": translate_env._("Administrators"),
        "description": translate_env._("General channel for administrators."),
    })
    env.ref("mail.module_install_notification").body = Markup("%s<br/>%s") % (
        translate_env._("Welcome to the #General channel 🎉"),
        translate_env._("This is a space for the whole team to connect and share updates."),
    )
