# -*- coding: utf-8 -*-
import sphinx.roles
import sphinx.environment
from sphinx.builders.html import StandaloneHTMLBuilder
from sphinx.writers.html import HTMLTranslator
from docutils.writers.html4css1 import HTMLTranslator as DocutilsTranslator

def patch():
    # navify toctree (oh god)
    @monkey(sphinx.environment.BuildEnvironment)
    def resolve_toctree(old_resolve, self, *args, **kwargs):
        """ If main_navbar, bootstrapify TOC to yield a navbar

        """
        main_navbar = kwargs.pop('main_navbar', False)
        toc = old_resolve(self, *args, **kwargs)
        if toc is None:
            return None

        navbarify(toc[0], main_navbar=main_navbar)
        return toc

    @monkey(StandaloneHTMLBuilder)
    def _get_local_toctree(old_local, self, *args, **kwargs):
        """ _get_local_toctree generates a documentation toctree for the local
        document (?), called from handle_page
        """
        # so can call toctree(main_navbar=False)
        d = {'main_navbar': True}
        d.update(kwargs)
        return old_local(self, *args, **d)

    # monkeypatch visit_table to remove border and add .table
    HTMLTranslator.visit_table = visit_table
    # disable colspec crap
    HTMLTranslator.write_colspecs = lambda self: None
    # copy data- attributes straight from source to dest
    HTMLTranslator.starttag = starttag_data

def navbarify(node, main_navbar=False):
    # add classes to toplevel
    if not main_navbar:
        navify([node])
    else:
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
            list_item['classes'].append('dropdown')
            # list_item.compact_paragraph.reference
            link = list_item.children[0].children[0]
            link['classes'].append('dropdown-toggle')
            link.attributes['data-toggle'] = 'dropdown'
            # list_item.bullet_list
            list_item.children[1]['classes'].append('dropdown-menu')
def navify(nodes):
    for node in nodes:
        if node.tagname == 'bullet_list':
            node['classes'].append('nav')
        navify(node.children)

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
