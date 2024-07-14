# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from . import controllers
from . import models
from . import populate
from . import wizard

from odoo.exceptions import UserError

def pre_init_knowledge(env):
    """ Some lxml arm64 versions cannot decode icons and cause the installation to crash.
    This will test to decode an emoji before the installation of the app, and show
    a helper message if it crashed.
    """
    try:
        etree.fromstring("<p>😀</p>")
    except etree.XMLSyntaxError:
        raise UserError(
            "The version of the lxml package used is not supported. "
            "Consider reinstalling lxml package using 'pip install --nobinary :all: lxml'")

def _init_private_article_per_user(env):
    env['res.users'].search([('partner_share', '=', False)])._generate_tutorial_articles()
