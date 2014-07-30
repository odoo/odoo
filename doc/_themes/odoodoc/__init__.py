# -*- coding: utf-8 -*-
from . import html_domain
# add Odoo style to pygments
from . import odoo_pygments

from . import sphinx_monkeypatch
sphinx_monkeypatch.patch()

def setup(app):
    html_domain.setup(app)
