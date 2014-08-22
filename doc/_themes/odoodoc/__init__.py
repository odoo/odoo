# -*- coding: utf-8 -*-
from . import html_domain
# add Odoo style to pygments
from . import odoo_pygments

from . import sphinx_monkeypatch
sphinx_monkeypatch.patch()

def setup(app):
    html_domain.setup(app)

    app.add_directive('exercise', Exercise)
    app.add_node(exercise, html=(
        lambda self, node: self.visit_admonition(node, 'exercise'),
        lambda self, node: self.depart_admonition(node)
    ))

from docutils import nodes
from docutils.parsers.rst.directives import admonitions
class exercise(nodes.Admonition, nodes.Element): pass
class Exercise(admonitions.BaseAdmonition):
    node_class = exercise

from sphinx.locale import admonitionlabels, l_
admonitionlabels['exercise'] = l_('Exercise')
