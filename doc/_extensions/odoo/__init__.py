# -*- coding: utf-8 -*-

from . import pygments_override
from . import switcher
from . import translator

import sphinx.environment
import sphinx.builders.html
from docutils import nodes
def setup(app):
    app.set_translator('html', translator.BootstrapTranslator)

    switcher.setup(app)
    app.add_config_value('odoo_cover_default', None, 'env')
    app.add_config_value('odoo_cover_external', {}, 'env')
    app.add_config_value('odoo_cover_default_external', lambda conf: conf.odoo_cover_default, 'env')
    app.connect('html-page-context', update_meta)

def update_meta(app, pagename, templatename, context, doctree):
    meta = context.setdefault('meta', {})
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
            # otherwise replace reference node by its own children
            para = n.parent
            para.remove(n)
            para.extend(n.children)


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
