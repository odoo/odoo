# $Id: __init__.py 8239 2018-11-21 21:46:00Z milde $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

"""
This package contains Docutils parser modules.
"""

__docformat__ = 'reStructuredText'

import sys
from docutils import Component


class Parser(Component):

    component_type = 'parser'
    config_section = 'parsers'

    def parse(self, inputstring, document):
        """Override to parse `inputstring` into document tree `document`."""
        raise NotImplementedError('subclass must override this method')

    def setup_parse(self, inputstring, document):
        """Initial parse setup.  Call at start of `self.parse()`."""
        self.inputstring = inputstring
        self.document = document
        document.reporter.attach_observer(document.note_parse_message)

    def finish_parse(self):
        """Finalize parse details.  Call at end of `self.parse()`."""
        self.document.reporter.detach_observer(
            self.document.note_parse_message)


_parser_aliases = {
      'restructuredtext': 'rst',
      'rest': 'rst',
      'restx': 'rst',
      'rtxt': 'rst',}

def get_parser_class(parser_name):
    """Return the Parser class from the `parser_name` module."""
    parser_name = parser_name.lower()
    if parser_name in _parser_aliases:
        parser_name = _parser_aliases[parser_name]
    try:
        module = __import__(parser_name, globals(), locals(), level=1)
    except ImportError:
        module = __import__(parser_name, globals(), locals(), level=0)
    return module.Parser
