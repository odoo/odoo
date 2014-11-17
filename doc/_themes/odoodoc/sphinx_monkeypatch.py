# -*- coding: utf-8 -*-
import sphinx.roles
import sphinx.environment
from sphinx.writers.html import HTMLTranslator
from docutils.writers.html4css1 import HTMLTranslator as DocutilsTranslator

def patch():
    # navify toctree (oh god)
    @monkey(sphinx.environment.BuildEnvironment)
    def resolve_toctree(old_resolve, self, *args, **kwargs):
        """ If navbar, bootstrapify TOC to yield a navbar

        """
        navbar = kwargs.pop('navbar', None)
        toc = old_resolve(self, *args, **kwargs)
        if toc is None:
            return None

        navbarify(toc[0], navbar=navbar)
        return toc

    # monkeypatch visit_table to remove border and add .table
    HTMLTranslator.visit_table = visit_table
    # disable colspec crap
    HTMLTranslator.write_colspecs = lambda self: None
    # copy data- attributes straight from source to dest
    HTMLTranslator.starttag = starttag_data

def navbarify(node, navbar=None):
    """
    :param node: toctree node to navbarify
    :param navbar: Whether this toctree is a 'main' navbar, a 'side' navbar or
                   not a navbar at all
    """
    if navbar == 'side':
        for n in node.traverse():
            if n.tagname == 'bullet_list':
                n['classes'].append('nav')
    elif navbar == 'main':
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
            if not list_item.children[1].children:
                return

            list_item['classes'].append('dropdown')
            # list_item.compact_paragraph.reference
            link = list_item.children[0].children[0]
            link['classes'].append('dropdown-toggle')
            link.attributes['data-toggle'] = 'dropdown'
            # list_item.bullet_list
            list_item.children[1]['classes'].append('dropdown-menu')

def visit_table(self, node):
    """
    * remove border
    * add table class
    """
    self._table_row_index = 0
    self.context.append(self.compact_p)
    self.compact_p = True
    classes = ' '.join({'table', self.settings.table_style}).strip()
    self.body.append(self.starttag(node, 'table', CLASS=classes))

def starttag_data(self, node, tagname, suffix='\n', empty=False, **attributes):
    attributes.update(
        (k, v) for k, v in node.attributes.iteritems()
        if k.startswith('data-')
    )
    # oh dear
    return DocutilsTranslator.starttag(
        self, node, tagname, suffix=suffix, empty=empty, **attributes)

class monkey(object):
    def __init__(self, obj):
        self.obj = obj
    def __call__(self, fn):
        name = fn.__name__
        old = getattr(self.obj, name)
        setattr(self.obj, name, lambda self_, *args, **kwargs: \
                fn(old, self_, *args, **kwargs))
