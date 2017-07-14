# -*- coding: utf-8 -*-
from .directives import automodule_bound
from .extractor import _read_js, _get_roots


def setup(app):
    app.add_config_value('js_roots', _get_roots, 'env')
    modules = {}
    symbols = {}
    app.connect('env-before-read-docs', _read_js(modules, symbols))
    app.add_directive_to_domain(
        'js', 'automodule',
        automodule_bound(app, modules, symbols)
    )
