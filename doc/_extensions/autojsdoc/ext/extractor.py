# -*- coding: utf-8 -*-
import io
import os

import pyjsdoc
import pyjsparser
from sphinx.util import status_iterator

from ..parser import jsdoc, parser


def _get_roots(conf):
    env_roots = os.environ.get('AUTOJSDOC_ROOTS_PATH')
    if env_roots:
        return env_roots.split(':')
    return []

def read_js(app, modules, symbols):
    """
    :type app: sphinx.application.Sphinx
    :type modules: Dict[str, jsdoc.ModuleDoc]
    :type symbols: Dict[str, jsdoc.CommentDoc]
    """
    roots = map(os.path.normpath, app.config.js_roots or [os.path.join(app.confdir, '..')])
    files = [
        os.path.join(r, f)
        for root in roots
        for r, _, fs in os.walk(root)
        if 'static/src/js' in r
        for f in fs
        if f.endswith('.js')
    ]

    modules.update((mod.name, mod) for mod in ABSTRACT_MODULES)
    for name in status_iterator(files, "Parsing javascript files...", length=len(files)):
        with io.open(name) as f:
            ast = pyjsparser.parse(f.read())
            modules.update(
                (mod.name, mod)
                for mod in parser.ModuleMatcher(name).visit(ast)
            )
    _resolve_references(modules)

    for mod in modules.values():
        exports = symbols[mod.name] = mod.exports
        graft(exports, symbols, prefix=mod.name)

def graft(parent, items, prefix):
    if isinstance(parent, jsdoc.ClassDoc):
        for m in parent.methods:
            items["%s.%s" % (prefix, m.name)] = m
    elif isinstance(parent, jsdoc.ObjectDoc):
        for name, p in parent.properties:
            path = "%s.%s" % (prefix, name)
            items[path] = p
            graft(p, items, path)

def _resolve_references(byname):
    # must be done in topological order otherwise the dependent can't
    # resolve non-trivial references to a dependency properly
    for name in pyjsdoc.topological_sort(
        *pyjsdoc.build_dependency_graph(
            list(byname.keys()),
            byname
        )
    ):
        byname[name].post_process(byname)

ABSTRACT_MODULES = [
    jsdoc.ModuleDoc({
        'module': u'web.web_client',
        'dependency': {u'web.AbstractWebClient'},
        'exports': jsdoc.NSDoc({
            'name': u'web_client',
            'doc': u'instance of AbstractWebClient',
        }),
    }),
    jsdoc.ModuleDoc({
        'module': u'web.Tour',
        'dependency': {u'web_tour.TourManager'},
        'exports': jsdoc.NSDoc({
            'name': u'Tour',
            'doc': u'maybe tourmanager instance?',
        }),
    }),
    jsdoc.ModuleDoc({
        'module': u'summernote/summernote',
        'exports': jsdoc.NSDoc({'doc': u"totally real summernote"}),
    })
]
