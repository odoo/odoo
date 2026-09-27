"""
The docstrings can use many more roles and directives than the one
present natively in docutils. That's because we use Sphinx to render
them in the documentation, and Sphinx defines the "Python Domain", a set
of additional rules and directive to understand the python language.

It is not desirable to add a dependency on Sphinx in community, as it is
a *too big* dependency.

The following code adds a bunch of dummy elements for the missing roles
and directives, so docutils is able to parse them with no warning.
"""

import docutils.nodes
import docutils.parsers.rst.directives.admonitions


def _role_literal(name, rawtext, text, lineno, inliner, options=None, content=None):
    literal = docutils.nodes.literal(rawtext, text)
    return [literal], []


def patch_module():
    for role in ('attr', 'class', 'func', 'meth', 'ref', 'const', 'samp', 'term'):
        docutils.parsers.rst.roles.register_local_role(role, _role_literal)

    for directive in ('attribute', 'deprecated'):
        docutils.parsers.rst.directives.register_directive(
            directive, docutils.parsers.rst.directives.admonitions.Note)
