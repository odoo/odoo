# -*- coding: utf-8 -*-

from . import pygments_override
from . import switcher
from . import translator

import sphinx.environment
try:
    from sphinx.environment.adapters import toctree
except ImportError:
    toctree = None

import sphinx.builders.html
from docutils import nodes
def setup(app):
    if hasattr(app, 'set_translator'):
        app.set_translator('html', translator.BootstrapTranslator)
    else:
        if getattr(app.config, 'html_translator_class', None):
            app.warn("Overriding the explicitly set  html_translator_class setting",
                     location="odoo extension")
        app.config.html_translator_class = 'odoo_ext.translator.BootstrapTranslator'

    add_js_file = getattr(app, 'add_js_file', None) or app.add_javascript
    for f in ['jquery.min.js', 'bootstrap.js', 'doc.js', 'jquery.noconflict.js']:
        add_js_file(f)

    switcher.setup(app)
    app.add_config_value('odoo_cover_default', None, 'env')
    app.add_config_value('odoo_cover_external', {}, 'env')
    app.add_config_value('odoo_cover_default_external', lambda conf: conf.odoo_cover_default, 'env')
    app.connect('html-page-context', update_meta)

def update_meta(app, pagename, templatename, context, doctree):
    meta = context.get('meta')
    if meta is None:
        meta = context['meta'] = {}
    meta.setdefault('banner', app.config.odoo_cover_default)

def navbarify(node, navbar=None):
    """
    :param node: toctree node to navbarify
    :param navbar: Whether this toctree is a 'main' navbar, a 'side' navbar or
                   not a navbar at all
    """
    if navbar == 'main':
        # add classes to just toplevel
        node['classes'].extend(['nav', 'navbar-nav', 'navbar-right'])
        for list_item in node.children:
            # bullet_list
            #     list_item
            #         compact_paragraph
            #             reference
            #         bullet_list
            #             list_item
            #                 compact_paragraph
            #                     reference
            # no bullet_list.list_item -> don't dropdownify
            if len(list_item.children) < 2 or not list_item.children[1].children:
                continue

            list_item['classes'].append('dropdown')
            # list_item.compact_paragraph.reference
            link = list_item.children[0].children[0]
            link['classes'].append('dropdown-toggle')
            link.attributes['data-toggle'] = 'dropdown'
            # list_item.bullet_list
            list_item.children[1]['classes'].append('dropdown-menu')
    elif navbar is None:
        for n in node.traverse(nodes.reference):
            # list_item
            #   compact_paragraph
            #       reference <- starting point
            #   bullet_list
            #       list_item+
            # if the current list item (GP of current node) has bullet list
            # children, unref it
            list_item = n.parent.parent
            # only has a reference -> ignore
            if len(list_item.children) < 2:
                continue
            # no subrefs -> ignore
            if not list_item.children[1].children:
                continue
            # otherwise replace reference node by an inline (so it can still be styled)
            para = n.parent
            para.remove(n)
            para.append(nodes.inline('', '', *n.children))


def resolve_content_toctree(
        environment, docname, builder, toctree, prune=True, maxdepth=0,
        titles_only=False, collapse=False, includehidden=False):
    """Alternative toctree resolution for main content: don't resolve the
    toctree, just handle it as a normal node, in the translator
    """
    return toctree

class monkey(object):
    def __init__(self, obj):
        self.obj = obj
    def __call__(self, fn):
        name = fn.__name__
        old = getattr(self.obj, name)
        setattr(self.obj, name, lambda self_, *args, **kwargs: \
                fn(old, self_, *args, **kwargs))
if toctree:
    # 1.6 and above use a new toctree adapter object for processing rather
    # than functions on the BuildEnv & al
    @monkey(toctree.TocTree)
    def resolve(old_resolve, tree, docname, *args, **kwargs):
        if docname == tree.env.config.master_doc:
            return resolve_content_toctree(tree.env, docname, *args, **kwargs)
        return old_resolve(tree, docname, *args, **kwargs)

@monkey(sphinx.environment.BuildEnvironment)
def resolve_toctree(old_resolve, self, docname, *args, **kwargs):
    """ If navbar, bootstrapify TOC to yield a navbar

    """
    navbar = kwargs.pop('navbar', None)
    if docname == self.config.master_doc and not navbar:
        return resolve_content_toctree(self, docname, *args, **kwargs)
    toc = old_resolve(self, docname, *args, **kwargs)
    if toc is None:
        return None

    navbarify(toc[0], navbar=navbar)
    return toc

@monkey(sphinx.builders.html.StandaloneHTMLBuilder)
def render_partial(old_partial, self, node):
    if isinstance(node, nodes.bullet_list) and node.children:
        # side nav?
        # remove single top-level item
        # bullet_list/0(list_item)/1(bullet_list)
        level1 = node.children[0].children
        if len(level1) > 1:
            node = level1[1]
            node['classes'].extend(['list-group', 'nav', 'text-left'])
            for n in node.traverse():
                if isinstance(n, nodes.list_item):
                    n['classes'].append('list-group-item')
                elif isinstance(n, nodes.reference):
                    n['classes'].append('ripple')
        else:
            node.clear()
    return old_partial(self, node)
