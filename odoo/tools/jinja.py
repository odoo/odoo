# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import copy
import dateutil.relativedelta as relativedelta
import functools
import logging

from werkzeug import urls

from odoo.tools import safe_eval

_logger = logging.getLogger(__name__)

def relativedelta_proxy(*args, **kwargs):
    # dateutil.relativedelta is an old-style class and cannot be directly
    # instanciated wihtin a jinja2 expression, so a lambda "proxy" is
    # is needed, apparently
    return relativedelta.relativedelta(*args, **kwargs)


try:
    # We use a jinja2 sandboxed environment to render mako templates.
    # Note that the rendering does not cover all the mako syntax, in particular
    # arbitrary Python statements are not accepted, and not all expressions are
    # allowed: only "public" attributes (not starting with '_') of objects may
    # be accessed.
    # This is done on purpose: it prevents incidental or malicious execution of
    # Python code that may break the security of the server.
    from jinja2.sandbox import SandboxedEnvironment
    from jinja2.nodes import Template, TemplateData, Output

    class JinjaInspectionSandboxedEnvironment(SandboxedEnvironment):
        """Environment used to retrieve the compiled code of the Jinja template."""

        def _parse(self, *args, **kwargs):
            self.current_code = super()._parse(*args, **kwargs)
            return self.current_code

        def from_string(self, source, *args, **kwargs):
            template = super().from_string(source, *args, **kwargs)
            template.code = self.current_code
            template.is_dynamic = self._is_current_code_dynamic()
            return template

        def _is_current_code_dynamic(self):
            """Detect if the current code is not purely static.

            Return True / False if the template is dynamic or not.

            A template is dynamic if it contains loop, conditions, comments, variables...

            After the compilation into the AST, if the code is purely static, the AST
            will be composed by only one node "TemplateData". If it's not the case, it
            means that the template contains Jinja code and will try to find the line
            number of this code.
            """
            if not isinstance(self.current_code, Template):
                return True

            if len(self.current_code.body) != 1:
                return True

            output = self.current_code.body[0]
            if not isinstance(output, Output):
                return True

            if len(output.nodes) != 1:
                return True

            template_data = output.nodes[0]
            if not isinstance(template_data, TemplateData):
                return True

            return False

    jinja_template_env = JinjaInspectionSandboxedEnvironment(
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

    template_env_globals = {
        'str': str,
        'quote': urls.url_quote,
        'urlencode': urls.url_encode,
        'datetime': safe_eval.datetime,
        'len': len,
        'abs': abs,
        'min': min,
        'max': max,
        'sum': sum,
        'filter': filter,
        'reduce': functools.reduce,
        'map': map,
        'relativedelta': relativedelta_proxy,
        'round': round,
    }

    jinja_template_env.globals.update(template_env_globals)
    jinja_safe_template_env = copy.copy(jinja_template_env)
    jinja_safe_template_env.autoescape = False
except ImportError:
    _logger.warning("jinja2 not available, templating features will not work!")
