# -*- coding: utf-8 -*-

"""
Adds a new "exercise" admonition type
"""

def setup(app):
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

from sphinx.locale import admonitionlabels
admonitionlabels['exercise'] = 'Exercise'
