# -*- coding: utf-8 -*-
from . import html_domain
from . import github
# add Odoo style to pygments
from . import odoo_pygments

from . import sphinx_monkeypatch
sphinx_monkeypatch.patch()

def setup(app):
    html_domain.setup(app)
    github.setup(app)

    app.add_directive('exercise', Exercise)
    app.add_node(exercise, html=(
        lambda self, node: self.visit_admonition(node, 'exercise'),
        lambda self, node: self.depart_admonition(node)
    ), latex=(
        lambda self, node: self.visit_admonition(node),
        lambda self, node: self.depart_admonition(node)
    ))

from docutils import nodes
from docutils.parsers.rst.directives import admonitions
class exercise(nodes.Admonition, nodes.Element): pass
class Exercise(admonitions.BaseAdmonition):
    node_class = exercise

from sphinx.locale import admonitionlabels, l_
admonitionlabels['exercise'] = l_('Exercise')

# monkeypatch PHP lexer to not require <?php
from sphinx.highlighting import lexers
from pygments.lexers.web import PhpLexer
lexers['php'] = PhpLexer(startinline=True)
