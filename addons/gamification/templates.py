# We use a jinja2 sandboxed environment to render mako templates.
# Note that the rendering does not cover all the mako syntax, in particular
# arbitrary Python statements are not accepted, and not all expressions are
# allowed: only "public" attributes (not starting with '_') of objects may
# be accessed.
# This is done on purpose: it prevents incidental or malicious execution of
# Python code that may break the security of the server.

from jinja2.sandbox import SandboxedEnvironment
from jinja2 import FileSystemLoader
    
from urllib import urlencode, quote as quote
import os.path

class TemplateHelper(SandboxedEnvironment):

    GAMIFICATION_PATH = os.path.dirname(os.path.abspath(__file__))

    def __init__(self):

        super(TemplateHelper,self).__init__(
            loader=FileSystemLoader(os.path.join(self.GAMIFICATION_PATH,'templates/')),
            block_start_string="<%",
            block_end_string="%>",
            variable_start_string="${",
            variable_end_string="}",
            comment_start_string="<%doc>",
            comment_end_string="</%doc>",
            line_statement_prefix="%",
            line_comment_prefix="##",
            trim_blocks=True,               # do not output newline after blocks
            autoescape=True,                # XML/HTML automatic escaping
        )
        self.globals.update({
            'str': str,
            'quote': quote,
            'urlencode': urlencode,
        })

