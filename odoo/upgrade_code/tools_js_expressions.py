from odoo.upgrade_code.tools_etree import get_indentation, update_etree
from lxml import etree
from collections import defaultdict

import re

# ------------------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------------------

RESERVED_WORDS = {
    "true",
    "false",
    "NaN",
    "null",
    "undefined",
    "debugger",
    "console",
    "window",
    "in",
    "instanceof",
    "new",
    "function",
    "return",
    "eval",
    "void",
    "Math",
    "RegExp",
    "Array",
    "Object",
    "Date",
    "__globals__",
    "None",  # technically not correct but will prevent crash
}

WORD_REPLACEMENT = {
    "and": "and",
    "or": "or",
    "gt": ">",
    "gte": ">=",
    "lt": "<",
    "lte": "<=",
}

STATIC_TOKEN_MAP = {
    "{": "LEFT_BRACE",
    "}": "RIGHT_BRACE",
    "[": "LEFT_BRACKET",
    "]": "RIGHT_BRACKET",
    "(": "LEFT_PAREN",
    ")": "RIGHT_PAREN",
    ",": "COMMA",
    ":": "COLON",
}

OPERATORS = [
    "...",
    ".",
    "===",
    "==",
    "+",
    "!==",
    "!=",
    "!",
    "||",
    "&&",
    ">=",
    ">",
    "<=",
    "=\u2007>",
    "<",
    "?",
    "-",
    "*",
    "/",
    "%",
    "typeof ",
    "=>",
    "=",
    ";",
    "in ",
    "new ",
    "|",
    "&",
    "^",
    "~",
]

# ------------------------------------------------------------------------------
# Token
# ------------------------------------------------------------------------------


class Token:
    def __init__(self, type_, value, size=None):
        self.type = type_
        self.value = value
        self.size = size or len(value)
        self.original_value = value
        self.var_name = None
        self.is_local = False


# ------------------------------------------------------------------------------
# Tokenizers
# ------------------------------------------------------------------------------


def tokenize_string(expr):
    if expr[0] not in ("'", '"', "`"):
        return None
    quote = expr[0]
    i = 1
    while i < len(expr):
        if expr[i] == "\\":
            i += 2
            continue
        if expr[i] == quote:
            s = expr[: i + 1]
            return Token("TEMPLATE_STRING" if quote == "`" else "VALUE", s)
        i += 1
    raise ValueError("Invalid string literal")


def tokenize_number(expr):
    m = re.match(r"\d+(\.\d+)?", expr)
    if m:
        return Token("VALUE", m.group(0))
    return None


def tokenize_symbol(expr):
    m = re.match(r"[a-zA-Z_$][\w$]*", expr)
    if not m:
        return None
    s = m.group(0)
    if s in WORD_REPLACEMENT:
        return Token("OPERATOR", s, len(s))
    return Token("SYMBOL", s)


def tokenize_operator(expr):
    for op in OPERATORS:
        if expr.startswith(op):
            return Token("OPERATOR", op)
    return None


def tokenize_static(expr):
    if expr[0] in STATIC_TOKEN_MAP:
        return Token(STATIC_TOKEN_MAP[expr[0]], expr[0])
    return None


TOKENIZERS = [
    tokenize_string,
    tokenize_number,
    tokenize_operator,
    tokenize_symbol,
    tokenize_static,
]


def tokenize(expr):
    tokens = []
    s = expr
    while s:
        # Capture leading whitespace as a VALUE token
        m = re.match(r"\s+", s)
        if m:
            tokens.append(Token("WHITESPACE", m.group(0)))
            s = s[m.end():]
            continue

        for t in TOKENIZERS:
            token = t(s)
            if token:
                tokens.append(token)
                s = s[token.size:]
                break
        else:
            raise ValueError(f"Tokenizer error near: {s}")
    return tokens

# ------------------------------------------------------------------------------
# Expression Compiler
# ------------------------------------------------------------------------------


TEMPLATE_EXPR = re.compile(r"\$\{([^}]+)\}")
INTERP_RE = re.compile(r"(#\{(.*?)\}|\{\{(.*?)\}\})")
LEADING_WHITESPACE_RE = re.compile(r'^\s*')
TRAILING_WHITESPACE_RE = re.compile(r'\s*$')
_AUTO_CLOSE_T = re.compile(r'(<t\b[^>]*\bt-(?:call|snippet-call)\s*=[^>]*[^/>])>\s*</t>', flags=re.MULTILINE)
_XPATH_TCALL_REG = re.compile(r'\[@(t-call)=[^\]]+\]$')


def next_non_whitespace(tokens, i):
    j = i + 1
    while j < len(tokens) and tokens[j].type == "WHITESPACE":
        j += 1
    return tokens[j] if j < len(tokens) else None


def prev_non_whitespace(tokens, i):
    j = i - 1
    while j >= 0 and tokens[j].type == "WHITESPACE":
        j -= 1
    return tokens[j] if j >= 0 else None


class ExpressionCompiler:
    """
    Compiles JavaScript expressions found inside XML templates, prefixing
    component-scoped variables with `this.`.
    """
    def __init__(self, warnings_list: list):
        self.warnings = warnings_list
        self.node_vars = set()
        self.warning_vars = set()
        self.outer_vars = set()
        self.template_name = ""

    def set_context(self, template_name: str, node_vars: set, warning_vars: set, outer_vars: set):
        """Updates the variable context for the current XML node being parsed."""
        self.template_name = template_name
        self.node_vars = node_vars
        self.warning_vars = warning_vars
        self.outer_vars = outer_vars.get(template_name, set())

    def compile_expr(self, expr: str) -> str:
        leading_ws = re.search(LEADING_WHITESPACE_RE, expr)[0]
        trailing_ws = re.search(TRAILING_WHITESPACE_RE, expr)[0]
        stripped = expr.strip()
        if not stripped:
            return expr

        tokens = tokenize(stripped)
        local_vars = set()
        stack = []  # track {, [, ( for group context

        i = 0
        while i < len(tokens):
            tok = tokens[i]
            if tok.type == "WHITESPACE":
                i += 1
                continue

            if tok.type == "TEMPLATE_STRING":
                def replace(match):
                    inner_expr = match.group(1)
                    rewritten = self.compile_expr(inner_expr)  # Recursive call
                    return "${" + rewritten + "}"
                tok.value = TEMPLATE_EXPR.sub(replace, tok.value)

            next_tok = next_non_whitespace(tokens, i)
            prev_tok = prev_non_whitespace(tokens, i)
            group_type = stack[-1] if stack else None

            # --- Track groups ---
            if tok.type in ("LEFT_BRACE", "LEFT_BRACKET", "LEFT_PAREN"):
                stack.append(tok.type)
            elif tok.type in ("RIGHT_BRACE", "RIGHT_BRACKET", "RIGHT_PAREN"):
                stack.pop()

            # Arrow detection
            is_arrow = False
            if next_tok and next_tok.type == "OPERATOR" and next_tok.value in ("=\u2007>", "=>"):
                is_arrow = True
            elif next_tok and next_tok.value == "=":
                next_next_tok = next_non_whitespace(tokens, tokens.index(next_tok))
                if next_next_tok and next_next_tok.value == "__xgtx__":
                    is_arrow = True

            if is_arrow:
                if tok.type == "RIGHT_PAREN":
                    # (a, b) => ...
                    j = i - 1
                    while j >= 0 and tokens[j].type != "LEFT_PAREN":
                        if tokens[j].type == "SYMBOL":
                            tokens[j].value = tokens[j].original_value
                            local_vars.add(tokens[j].value)
                        j -= 1
                elif tok.type == "SYMBOL":
                    local_vars.add(tok.value)

            # Variable rewrite
            if (
                tok.type == "SYMBOL"
                and tok.value not in RESERVED_WORDS
                and tok.value not in self.node_vars
                and tok.value not in local_vars
                and not UNMASK_RE.fullmatch(tok.value)
                and tok.value != "this"
                and not (prev_tok and prev_tok.type == "OPERATOR" and prev_tok.value == ".")
                and not (
                    prev_tok
                    and (prev_tok.type == "LEFT_BRACE" or prev_tok.type == "COMMA")
                    and next_tok
                    and next_tok.type == "COLON"
                )
            ):
                # if tok.value in self.warning_vars:
                # self.warnings.append(f"WARNING in template '{self.template_name}' : variable '{tok.value}' also defined in a far parent.")

                if (
                    group_type == "LEFT_BRACE"
                    and prev_tok
                    and (prev_tok.type == "LEFT_BRACE" or prev_tok.type == "COMMA")
                    and next_tok
                    and (next_tok.type == "RIGHT_BRACE" or next_tok.type == "COMMA")
                ):
                    tok.value = f"{tok.value}: this.{tok.value}"
                else:
                    tok.value = f"this.{tok.value}"

            i += 1

        compiled = "".join((t.value) for t in tokens)
        return leading_ws + compiled + trailing_ws

    def process_dynamic_string(self, text: str) -> str:
        """Handles strings with embedded expressions like #{...} or {{...}}"""
        def repl(match):
            expr = match.group(2) if match.group(2) is not None else match.group(3)

            leading_ws = re.search(LEADING_WHITESPACE_RE, expr)[0]
            trailing_ws = re.search(TRAILING_WHITESPACE_RE, expr)[0]
            stripped_expr = expr.strip()
            if not stripped_expr:
                return match.group(0)

            compiled = self.compile_expr(stripped_expr)

            if match.group(2) is not None:
                return f"#{{{leading_ws}{compiled}{trailing_ws}}}"
            else:
                return f"{{{{{leading_ws}{compiled}{trailing_ws}}}}}"

        return INTERP_RE.sub(repl, text)


# ------------------------------------------------------------------------------
# Template
# ------------------------------------------------------------------------------

class Template:
    def __init__(self, name: str, is_testing: bool = False):
        self.is_testing = is_testing
        self.name = name
        self.parent = None
        self.children = set()
        self.calls_from = set()
        self.calls_to = set()
        self.dynamic_calls_to = set()
        self.file_path = None

    def _add_dependencies(self, dependencies: list[str]):
        for called_template in self.calls_from:
            if called_template.name in dependencies:
                continue
            dependencies.append(called_template.name)
            called_template._add_dependencies(dependencies)
        if self.parent is not None and self.parent.name not in dependencies:
            dependencies.append(self.parent.name)
            self.parent._add_dependencies(dependencies)

    def get_dependencies(self):
        deps = []
        self._add_dependencies(deps)
        return deps

    def get_inherit_chain(self):
        chain = []
        parent = self.parent
        while parent is not None:
            chain.append(parent.name)
            parent = parent.parent
        return chain

    def is_parent_component_template(self):
        return self.parent is not None and self.parent.is_component_template()

    def is_self_called(self):
        if self.is_testing:
            return False
        return any(template == self for template in self.calls_from)

    def is_called_by_component_template(self):
        if self.is_testing:
            return False
        for template in self.calls_from:
            if template == self:
                continue
            if template.is_component_template():
                return True
        return False

    def is_component_template(self):
        return not self.is_testing and self.is_parent_component_template() or self.is_called_by_component_template()

    def set_parent(self, parent):
        self.parent = parent
        parent.children.add(self)

    def add_dynamic_call_to_template(self, expr):
        self.dynamic_calls_to.add(expr)

    def add_call_to_template(self, template):
        self.calls_to.add(template)
        template.calls_from.add(self)


class ComponentRootTemplate(Template):
    def is_parent_component_template(self):
        return not self.is_testing

    def is_called_by_component_template(self):
        return not self.is_testing

    def is_component_template(self):
        return not self.is_testing


# ------------------------------------------------------------------------------
# Variables
# ------------------------------------------------------------------------------


class VariableAggregator:
    """
        Traverses XML templates, aggregating variables per fragment. The implementation
        does not take nested inherits or t-call vars into account on purpose (which we handle
        with warning).
    """

    def __init__(self, component_templates: list[str] = list(), is_testing: bool = False):
        self.all_templates = defaultdict()
        self.duplicated_template_name = defaultdict()
        self.is_testing = is_testing
        for template_name in component_templates:
            self.all_templates[template_name] = ComponentRootTemplate(template_name)
        self.all_vars = defaultdict(set)
        self.t_call_vars = defaultdict(set)
        self.t_call_outer_vars = defaultdict(set)

        self.inherit_map = defaultdict(str)  # TODO move to template parser
        self.full_inherit_and_call_map = defaultdict(str)  # TODO Template parser

    def add_template(self, template_name: str):
        if template_name not in self.all_templates:
            self.all_templates[template_name] = Template(template_name, self.is_testing)
        return self.all_templates[template_name]

    def link_templates(self, root: etree._ElementTree, file_path: str = 'anonymous'):
        templates = root.xpath("descendant-or-self::*[@t-name] | descendant-or-self::*[@t-inherit]")
        for template_node in templates:
            template_name = ''
            if 't-name' in template_node.attrib:
                template_name = template_node.attrib['t-name']
            else:
                count = self.duplicated_template_name.get(file_path, 0) + 1
                self.duplicated_template_name[file_path] = count
                template_name = file_path + str(count)
            template = self.add_template(template_name)
            template.file_path = file_path

            if 't-inherit' in template_node.attrib:
                inherit_template_name = template_node.attrib['t-inherit']
                if inherit_template_name == template_name:
                    count = self.duplicated_template_name.get(template_name, 0) + 1
                    self.duplicated_template_name[template_name] = count
                    template_name += str(count)
                else:
                    inherit_template = self.add_template(inherit_template_name)
                    template.set_parent(inherit_template)

            calls_to_nodes = template_node.xpath("descendant-or-self::*[@t-call]")
            for calls_to_node in calls_to_nodes:
                called_template_name = calls_to_node.attrib['t-call']
                if called_template_name.startswith('{{'):
                    template.add_dynamic_call_to_template(called_template_name)
                else:
                    called_template = self.add_template(called_template_name)
                    template.add_call_to_template(called_template)

    def aggregate_call_vars(self, root: etree._ElementTree):
        """
            Maps all variable inside t-call by t-call keys eg.
            <t t-call ="web.xyz"> <t t-set="x" t-value=2/> </t>  --> {"web.xyz" : {"x"}}
        """
        # Find all nodes with t-call="sometemplate"
        for call_node in root.xpath("descendant-or-self::*[@t-call]"):
            template_name = call_node.get("t-call")
            if not template_name:
                continue

            # Look for t-set inside this t-call subtree
            # (On purpose only take t-set inside t-call even if those outside still apply)
            for set_node in call_node.xpath("descendant-or-self::*[@t-set]"):
                var_name = set_node.get("t-set")
                if var_name:
                    self.t_call_vars[template_name].add(var_name)

            # Collect inline parameters on t-call (OWL 3 syntax: <t t-call="x" param="val"/>)
            # Skip when t-call is a direct child of t-inherit (attrs are xpath directives)
            parent = call_node.getparent()
            if parent is None or 't-inherit' not in parent.attrib:
                for attr in call_node.attrib:
                    if not attr.startswith("t-") and attr not in SKIP_XPATH_ATTRS:
                        self.t_call_vars[template_name].add(attr.replace('.translate', ''))

            scope_nodes = call_node.xpath("ancestor::* | ancestor-or-self::*/preceding-sibling::*")
            self.t_call_outer_vars[template_name].update(self._extract_vars_from_nodes(scope_nodes))

    def aggregate_inside_vars(self, root: etree._ElementTree):
        """
            Maps all variable inside a template in a dict keyed by template name.
        """
        templates = root.xpath("descendant-or-self::*[@t-name]")
        for tpl in templates:
            template_name = tpl.get("t-name")
            nodes = tpl.xpath("descendant-or-self::*[not(ancestor::*[@t-call])]")
            self.all_vars[template_name].update(self._extract_vars_from_nodes(nodes))

    def map_inherits_and_calls(self):
        if self.all_templates:
            for template_name in self.all_templates:

                template = self.all_templates[template_name]
                self.full_inherit_and_call_map[template_name] = template.get_dependencies()

                if template.parent is not None:
                    self.inherit_map[template_name] = template.parent.name

    @staticmethod
    def _extract_vars_from_nodes(nodes):
        """
            Helper generator that yields variable names found in a given iterable of XML nodes.
            Checks for t-set, t-as, t-index, and t-slot-scope.
        """
        for node in nodes:
            var_name = node.get("t-set")
            if var_name:
                yield var_name

            if node.get("t-foreach") or node.get("t-for-each"):
                var_name = node.get("t-as")
                if var_name:
                    yield var_name

                var_name = node.get("t-foreach-index") or node.get("t-index")
                if var_name:
                    yield var_name

            if node.get("t-slot-scope"):
                var_name = node.get("t-slot-scope")
                if var_name:
                    yield var_name


# ------------------------------------------------------------------------------
# Template Compiler
# ------------------------------------------------------------------------------


SKIP_XPATH_ATTRS = {"name", "ref", "set-slot", "slot", "call-slot"}  # attributes to skip
T_ATTR_RE = re.compile(r"@t-([\w-]+)='(.*?)'")  # For eg xpath=expr="[@t-if]"
EVENT_ATTR_RE = re.compile(r"(@(?:onSelected|onChange)(?:\.[\w-]+)?)='(.*?)'")
COMPONENT_TARGET_RE = re.compile(r"^.*/[A-Z][\w\-]*(?:\[.*?\])*$")  # This regex ensures the *last* node in the path starts with an uppercase letter.
VALUE_ATTR_RE = re.compile(r"(@value)='(.*?)'")
ENTITY_RE = re.compile(r"&([A-Za-z0-9#]{2,5});")
UNMASK_RE = re.compile(r"__x([A-Za-z0-9#]{2,5})x__")
MODULE_NAME_RE = re.compile(r'/([\w_]+)/static/')


def is_inside_inherit(node: etree._Element):
    """ Returns the nearest ancestor (or self) that defines a t-inherit. """
    return node.xpath("ancestor-or-self::*[@t-inherit][1]")


def get_inheritance_chain(template_name, inherit_map):
    chain = [inherit_map.get(template_name)]
    current = template_name

    seen = set()

    while current in inherit_map:
        if current in seen:
            break  # Break out of accidental circular dependencies

        seen.add(current)
        parent = inherit_map[current]
        chain.append(parent)
        current = parent

    return chain


def mask_xml_entities(text):
    """Convert XML entities like &apos; to __apos__ before parsing."""
    def repl(match):
        name = match.group(1)
        # skip masking &amp;
        return match.group(0) if name == "amp" else f"__x{name}x__"
    return ENTITY_RE.sub(repl, text)


def unmask_xml_entities(text):
    """Restore masked entities back to XML form."""
    return UNMASK_RE.sub(r"&\1;", text)


def iter_elements(root):
    """Yield only real element nodes (skip comments, PIs, etc.)"""
    for node in root.iter():
        # node.tag is a string for real elements
        if isinstance(node.tag, str):
            yield node


DIRECTIVES = [
    "t-att",
    "t-esc",
    "t-out",
    "t-value",
    "t-key",
    "t-if",
    "t-elif",
    "t-foreach",
    "t-component",
    "t-props",
    "t-tag",
    "t-call-context",
]


class TemplateCompiler:
    """
    Traverses XML templates to prefix component-scoped variables with `this.` file per file.

    It relies on precompiled template metadata dictionaries (variables, inheritance chain..)
    built with the VariableAggregator.

    Attributes:
        path: str: The path of the file we are procesing
        modules: list[str] - Process only templates with t-name or t-inherit starting with modules[x]*
        aggregator: VariableAggregator - template metadata
        excluded_templates: set[str] - List of template names to skip (also skip all template childs - except dynamic t-calls one)
    """

    def __init__(
            self,
            path: str,
            modules: list[str],
            aggregator: VariableAggregator,
            excluded_templates: set[str],
    ):
        self.t_call_vars = aggregator.t_call_vars
        self.t_call_outer_vars = aggregator.t_call_outer_vars
        self.all_vars = aggregator.all_vars
        self.inherit_map = aggregator.inherit_map
        self.full_inherit_and_call_map = aggregator.full_inherit_and_call_map
        self.all_templates = aggregator.all_templates
        self.duplicated_template_name = defaultdict()

        self.modules = modules
        self.template_path = path
        self.current_template = path  # default to the file path but if inside a t-name takes that value
        self.excluded_templates = excluded_templates
        self.warnings = []
        self.is_testing = aggregator.is_testing

        self.expr_compiler = ExpressionCompiler(self.warnings)

        # Dynamic attributes can change on each nodes
        self.node_vars = set()
        self.warning_vars = set()

    def fix_rendering_context(self, root: etree._ElementTree):
        template_nodes = root.xpath("descendant-or-self::*[@t-name] | descendant-or-self::*[@t-inherit]")
        # Filter out t-name used for positioning inside xpath
        template_nodes = [n for n in template_nodes if not ("position" in n.attrib and "t-inherit" not in n.attrib)]
        if template_nodes:
            for template in template_nodes:
                self.current_template = self._get_template_name(template)
                if self._should_skip_template(self.current_template):
                    continue

                # Bound vars are variables that are valid for the entire template
                bound_variables = self._collect_bound_variables(template)
                bound_variables |= set(self.t_call_vars.get(self.current_template, {}))
                bound_variables |= set(self.t_call_outer_vars.get(self.current_template, {}))  # We initially separated outer t-call vars and vars inside a t-call
                bound_variables |= set(self.all_vars.get(self.current_template, {}))

                self.fix_template(template, bound_variables)

        else:
            bound_variables = self._collect_bound_variables(root)
            self.fix_template(root, bound_variables)

    def fix_template(self, root: etree._ElementTree, bound_variables):
        """ Taverse node by node, changing variable context iteractively, and applying
            replacing logic based on node tags """
        for node in iter_elements(root):
            if self._should_skip_node(node):
                continue

            foreach_vars = set()
            for el in [node, *node.iterancestors()]:
                t_as = el.get("t-as")
                if t_as:
                    foreach_vars |= self._expand_t_as(t_as)
            self._set_node_vars(node, bound_variables | foreach_vars)

            if node.tag == "xpath":
                node.set("expr", self._process_xpath_expr(node))
            elif node.tag == "attribute":
                self._process_attribute(node)
                continue

            for d in DIRECTIVES:
                if d in node.attrib:
                    val = node.get(d)
                    if val:
                        node.set(d, self.expr_compiler.compile_expr(val))

            for attr, value in node.attrib.items():
                if attr.startswith("t-on-") and value:
                    node.set(attr, self.expr_compiler.compile_expr(value))
                if attr.startswith("t-att-") and not attr.startswith("t-attf-"):
                    node.set(attr, self.expr_compiler.compile_expr(value))
                if attr.startswith(("t-model", "t-custom-model", "t-portal", "t-custom-portal")) and value:
                    node.set(attr, self.expr_compiler.compile_expr(value))
                if attr.startswith("t-attf-"):
                    self._process_dynamic_attribute(node, attr)
                if attr in ('t-call', 't-ref', 't-custom-ref', 't-slot', 't-call-slot'):
                    self._process_dynamic_attribute(node, attr)

            if 't-call' in node.attrib:
                parent = node.getparent()
                if parent is None or 't-inherit' not in parent.attrib:
                    for attr, value in node.attrib.items():
                        if not attr.startswith('t-') and attr not in SKIP_XPATH_ATTRS and not attr.endswith('.translate') and value:
                            node.set(attr, self.expr_compiler.compile_expr(value))

            if 't-slot' in node.attrib or 't-call-slot' in node.attrib or 't-set-slot' in node.attrib:
                for attr, value in node.attrib.items():
                    if not attr.startswith('t-'):
                        node.set(attr, self.expr_compiler.compile_expr(value))

            if self._is_component(node):
                for attr, value in node.attrib.items():
                    if not value:
                        continue
                    if attr.startswith("t-") or attr.endswith(".translate"):
                        continue  # skip Owl directives
                    if is_inside_inherit(node) and attr.startswith("position"):
                        continue  # A component can be replaced with <A position="replace"/> inside inherits
                    node.set(attr, self.expr_compiler.compile_expr(value))

    def _should_skip_template(self, template_name: str):
        if self.current_template in self.excluded_templates:
            return True

        if self.is_testing:
            return False

        if template_name not in self.all_templates:
            return True

        template = self.all_templates[template_name]
        if template.file_path is None:
            return True

        inherit_chain = template.get_inherit_chain()
        if inherit_chain:
            template = self.all_templates[inherit_chain[-1]]
            if template.file_path is None:
                return True

        if not self.modules:
            return False
        return not any(module in re.search(MODULE_NAME_RE, template.file_path)[1] for module in self.modules)

    def _should_skip_node(self, node: etree._Element):
        """
            Skips non-element nodes (eg. comments), inherits targeting modules
            outside the target scope, and nodes in external files that
            are not under an inherit block from target scope.
        """

        if not isinstance(node.tag, str):
            return True  # eg. comments

        if is_inside_inherit(node):
            chain = get_inheritance_chain(self.current_template, self.inherit_map)
            for parent in chain:
                if parent in self.excluded_templates:
                    return True  # Don't refactor template inheriting renderAt templates

        if self.modules:
            # Logic only if targetting specific modules
            if is_inside_inherit(node):
                parent = is_inside_inherit(node)[0].get("t-inherit", "").split(".")[0]
                is_target = any(parent == m or parent.startswith(f"{m}_") for m in self.modules)
                if not is_target:
                    return True   # Don't refactor inherits targetting modules we are not refactoring
            else:
                in_folder = any(f"/{m}/" in self.template_path or f"/{m}_" in self.template_path for m in self.modules)
                if not in_folder:
                    return True  # Don't refactor templates not inside targer folder and not inheriting target

        return False

    def _process_dynamic_attribute(self, node, attr="t-attf-class"):
        value = node.get(attr)
        if not value:
            return

        new_value = self.expr_compiler.process_dynamic_string(value)
        node.set(attr, new_value)

    def _set_node_vars(self, node: etree._Element, base_vars: set[str]) -> set[str]:
        """ If inside a t-inherit subtree, merge target template locals into the vars. """
        if is_inside_inherit(node):
            target = is_inside_inherit(node)[0].get("t-inherit")
            self.node_vars = base_vars | (self.all_vars.get(target, set())) | self.t_call_vars.get(target, set())
        else:
            self.node_vars = base_vars
        # Now set warning vars
        if self.full_inherit_and_call_map.get(self.current_template):
            for parent in self.full_inherit_and_call_map.get(self.current_template):
                self.node_vars |= self.all_vars.get(parent, set())

        self.expr_compiler.set_context(
            template_name=self.current_template,
            node_vars=self.node_vars,
            warning_vars=self.warning_vars,
            outer_vars=self.t_call_outer_vars
        )

    def _process_attribute(self, node: etree._Element):
        """ Static handler for <attribute> nodes processing """
        attr_name = node.get("name")
        txt = node.text or ""

        if not txt.strip() and not (node.get("add", False) or node.get("remove", False)):
            return

        # Locate the parent xpath expression to decide if we should compile
        xp = node.xpath("ancestor::xpath[@expr][1]")
        xp_expr = xp[0].get("expr") if xp else ""

        if self._should_compile_attribute_node(attr_name, xp_expr):
            compile_expr = self.expr_compiler.compile_expr
            if attr_name and attr_name.startswith("t-attf-"):
                compile_expr = self.expr_compiler.process_dynamic_string

            if node.get("add") or node.get("remove"):
                if node.get("add"):
                    node.set("add", compile_expr(node.get("add")))
                if node.get("remove"):
                    node.set("remove", compile_expr(node.get("remove")))
            else:
                node.text = etree.CDATA(compile_expr(txt))

    def _process_xpath_expr(self, node: etree._Element):
        def repl(match):
            attr_name = match.group(1)
            js_expr = match.group(2)
            if attr_name in SKIP_XPATH_ATTRS:
                # return original string unchanged
                return match.group(0)
            if attr_name in ["call", "custom-ref", "ref"]:
                new_expr = self.expr_compiler.process_dynamic_string(js_expr)
            else:
                new_expr = self.expr_compiler.compile_expr(js_expr)
            # preserve quotes
            return match.group(0).replace(js_expr, new_expr)

        expr = node.get("expr")
        if expr:
            expr = T_ATTR_RE.sub(repl, expr)
            if COMPONENT_TARGET_RE.search(expr):
                expr = EVENT_ATTR_RE.sub(repl, expr)  # eg. //DropdownItem[@onSelected.bind='exportAuditReportToPDF']
                expr = VALUE_ATTR_RE.sub(repl, expr)  # eg. //CheckBox[@value='includeArchived']"
            return expr
        return node

    def _get_template_name(self, node: etree._Element):
        template_name = ''
        if 't-name' in node.attrib:
            template_name = node.attrib['t-name']
        else:
            template_path = self.template_path or 'anonymous'
            count = self.duplicated_template_name.get(template_path, 0) + 1
            self.duplicated_template_name[template_path] = count
            template_name = template_path + str(count)

        if 't-inherit' in node.attrib:
            inherit_template_name = node.attrib['t-inherit']
            if inherit_template_name == template_name:
                count = self.duplicated_template_name.get(template_name, 0) + 1
                self.duplicated_template_name[template_name] = count
                template_name += str(count)

        return template_name

    @staticmethod
    def _expand_t_as(name):
        return {name, f"{name}_index", f"{name}_first", f"{name}_last", f"{name}_value"}

    @staticmethod
    def _collect_bound_variables(root: etree._ElementTree):
        bound = set()
        for el in iter_elements(root):
            t_set = el.get("t-set")
            if t_set:
                bound.add(t_set)
            t_scope = el.get("t-slot-scope")
            if t_scope:
                bound.add(t_scope)
        return bound

    @staticmethod
    def _is_component(node: etree._Element):
        return (node.tag and node.tag[0].isupper()) or node.get("t-component") is not None

    @staticmethod
    def _should_compile_attribute_node(attr_name: str, xp_expr: str) -> bool:
        def is_component_xpath_expr(expr: str) -> bool:
            # component tag selection: //Navbar, //MyComp, etc.
            if expr and COMPONENT_TARGET_RE.match(expr):
                return True
            # t-component selection: //t[@t-component='...']
            return expr and ("@t-component" in expr or "t-component" in expr)

        if not attr_name:
            return False

        if attr_name in DIRECTIVES or attr_name.startswith(("t-on-", "t-att-", "t-attf-")):
            return True

        if attr_name in SKIP_XPATH_ATTRS:
            return False

        return is_component_xpath_expr(xp_expr)


# ------------------------------------------------------------------------------
# Parametric t-call transformation helpers
# ------------------------------------------------------------------------------


def _detach_node_tail(node):
    if (prev := node.getprevious()) is not None:
        prev.tail = (prev.tail or '').rstrip() + (node.tail or '')
    else:
        parent = node.getparent()
        parent.text = (parent.text or '').rstrip() + (node.tail or '')


def _move_tset_before_tcall(tset, tcall):
    parent = tcall.getparent()
    previous_indent = get_indentation(tset)
    indent = get_indentation(tcall)

    _detach_node_tail(tset)
    tset.tail = indent

    tset.set('__need_dedent__', str(len(previous_indent) - len(indent)))

    parent.insert(parent.index(tcall), tset)


def _remove_tset_add_attribute(tset, tcall):
    _detach_node_tail(tset)

    if 't-value' in tset.attrib:
        value = tset.get('t-value')
        tcall.set(tset.get('t-set'), value)
    else:
        tcall.set(f"{tset.get('t-set')}.translate", (tset.text or '').strip())

    tset.getparent().remove(tset)


def _is_not_direct_children_of(tset, tcall):
    closest_tcall = tset.xpath('ancestor::t[@t-call or @t-if or @t-elif or @t-else or @t-set or @t-foreach]')
    return closest_tcall and closest_tcall[-1] != tcall


def _varname_is_used_inside(tset, tcall):
    n = tset
    while (skip_to := n.getnext()) is None and n != tcall:
        n = n.getparent()
    if skip_to is None:
        return set()
    return __varname_is_used_inside(tset, tcall, skip_to)


def __varname_is_used_inside(tset, container, skip_to):
    used = set()
    varname = tset.get('t-set')
    REG = re.compile(rf"(^|[,({{ /*+-]){varname}([\[\] .()}}/*+-]|$)")

    for el in container.iter():
        if skip_to is not None and el is not skip_to:
            continue
        skip_to = None
        if not el.tag:
            continue

        for attr, value in el.attrib.items():
            if not attr.startswith('t-'):
                if el.attrib.get('t-call') and REG.search(value):
                    used.add('used')
            elif attr == 't-set' or attr == 't-as':
                if value == varname:
                    closest_tcall = el.xpath('ancestor::t[@t-call]')
                    if closest_tcall and closest_tcall[-1] == container:
                        used.add('rewrite')
            elif REG.search(value):
                used.add('current-used')

        is_tset = el.get('t-set')
        if is_tset:
            if len(el) and __varname_is_used_inside(tset, el, el[0]):
                used.add('current-used')
            skip_to = el.getnext()

        if 'current-used' in used:
            used.remove('current-used')
            if is_tset:
                sub_used = _varname_is_used_inside(el, container) - {'rewrite'}
                if sub_used:
                    used.update(sub_used)
                else:
                    if _is_not_direct_children_of(tset, container):
                        used.add('used')
                    else:
                        used.add('t-set')
            else:
                used.add('used')

    return used


def _remove_tset_add_inherit_attribute(tset, container):
    attribute = etree.Element('attribute')
    if len(container):
        container[-1].tail = container.text  # indent
    container.append(attribute)

    if 't-value' in tset.attrib:
        value = tset.get('t-value')
        attribute.attrib['name'] = tset.get('t-set')
        attribute.text = value
    elif not len(tset):
        attribute.attrib['name'] = f"{tset.get('t-set')}.translate"
        attribute.text = (tset.text or '').strip()
    else:
        raise ValueError('Wrong conversion')

    if tset.getparent() is not None:
        tset.getparent().remove(tset)


def _apply_parametric_tcall(tree, path, warnings):
    for tcall in tree.xpath('//*[@t-call or @t-snippet-call][not(@position="inside")]'):

        if any(not att.startswith('t-') for att in tcall.attrib):
            continue

        for tset in tcall.xpath('.//*[@t-set]'):
            if _is_not_direct_children_of(tset, tcall):
                continue

            used = _varname_is_used_inside(tset, tcall)

            if 'used' in used:
                continue

            if 'rewrite' in used:
                warnings.append(
                    f"Can not determine the position of the rewrited t-set: '{tset.get('t-set')}' in '{path}'"
                )
                break

            if ('t-set' in used or (len(tset) or tset.get('t-if'))):
                _move_tset_before_tcall(tset, tcall)
                tcall.set(tset.get('t-set'), tset.get('t-set'))
            else:
                _remove_tset_add_attribute(tset, tcall)

    # inherit t-call
    inherit_tcalls = (
        tree.xpath('//*[@t-call][@position="inside"]') +
        [
            tcall for tcall in tree.xpath('//xpath[contains(@expr, "@t-call")][@position="inside"]')
            if _XPATH_TCALL_REG.search(tcall.get('expr'))
        ]
    )
    for tcall in inherit_tcalls:
        parent = tcall.getparent()
        index = parent.index(tcall)
        indent = get_indentation(tcall)
        before = None
        attributes = None
        for tset in tcall.xpath('t[@t-set]'):
            _detach_node_tail(tset)

            if attributes is None:
                attributes = etree.Element(tcall.tag, tcall.attrib)
                attributes.attrib['position'] = 'attributes'
                attributes.text = indent + ' ' * 4
                attributes.tail = indent
                parent.insert(index, attributes)

            t_set_key = tset.get('t-set')
            if len(tset) or _varname_is_used_inside(tset, tcall):
                if before is None:
                    before = etree.Element(tcall.tag, tcall.attrib)
                    before.attrib['position'] = 'before'
                    before.text = indent + ' ' * 4
                    before.tail = indent
                    parent.insert(index, before)

                before.append(tset)
                tset = etree.Element('t', {'t-set': t_set_key, 't-value': t_set_key})

            _remove_tset_add_inherit_attribute(tset, attributes)

        if before is not None:
            before[-1].tail = indent
        if attributes is not None:
            attributes[-1].tail = indent

        if not len(tcall):
            _detach_node_tail(tcall)
            parent.remove(tcall)


def update_template(path: str, content: str, modules: list[str], aggregator: VariableAggregator, excluded_templates: set[str], *,
                    apply_tcall_param: bool = False, apply_this: bool = True):
    warnings = []
    compiler = None
    if apply_this:
        compiler = TemplateCompiler(path, modules, aggregator, excluded_templates)
        warnings = compiler.warnings

    content = mask_xml_entities(content)

    def callback(tree):
        if apply_tcall_param:
            _apply_parametric_tcall(tree, path, warnings)
        if apply_this:
            compiler.fix_rendering_context(tree)

    result = update_etree(content, callback)
    result = unmask_xml_entities(result)
    result = result.replace("><![CDATA[", ">").replace("]]>", "")
    result = result.replace("\u200b", "&#8203;")
    result = result.replace("&&", "&amp;&amp;")
    result = result.replace(") =&gt;", ") =>")
    result = _AUTO_CLOSE_T.sub(r"\g<1>/>", result)
    return result, warnings

# ------------------------------------------------------------------------------
# TESTS
# ------------------------------------------------------------------------------


def run_tests_main(test):
    res, _ = update_template("", test["content"], [], VariableAggregator(is_testing=True), {})
    return res


def run_tests_tcall_param(test):
    res, _ = update_template("", test["content"], [], None, None, apply_tcall_param=True, apply_this=False)
    return res


tests = [
    {
        "name": "t-call-context",
        "content": """<t t-call="a" t-call-context="renderingContext"/>""",
        "expected": """<t t-call="a" t-call-context="this.renderingContext"/>""",
    },
    {
        "name": "t foreach variation",
        "content": """
<t>
    <t t-name="web.OverlayContainer">
        <t t-foreach="sortedOverlays" t-as="overlay" t-key="overlay.id">
        </t>
    </t>
    <t t-name="blabla">
    </t>
</t>
""",
        "expected": """
<t>
    <t t-name="web.OverlayContainer">
        <t t-foreach="this.sortedOverlays" t-as="overlay" t-key="overlay.id">
        </t>
    </t>
    <t t-name="blabla">
    </t>
</t>
""",
    },
    {
        "name": "dynamic t-call",
        "content": """<t t-call="{{ getAuthMethodFormTemplate(state.authMethod) }}"/>""",
        "expected": """<t t-call="{{ this.getAuthMethodFormTemplate(this.state.authMethod) }}"/>""",
    },
    {
        "name": "dynamic t-ref",
        "content": """<t t-ref="{{ getAuthMethodFormTemplate(state.authMethod) }}"/>""",
        "expected": """<t t-ref="{{ this.getAuthMethodFormTemplate(this.state.authMethod) }}"/>""",
    },
    {
        "name": "template string",
        "content": """<b t-esc="`(${timeDuration})`" />""",
        "expected": """<b t-esc="`(${this.timeDuration})`" />""",
    },
    {
        "name": "dynamic t-slot",
        "content": """<t t-slot="{{ d }}"/>""",
        "expected": """<t t-slot="{{ this.d }}"/>""",
    },
    {
        "name": "dynamic t-call-slot",
        "content": """<t t-call-slot="{{ d }}"/>""",
        "expected": """<t t-call-slot="{{ this.d }}"/>""",
    },
    {
        "name": "t-model",
        "content": '<input t-model="state.value"/>',
        "expected": '<input t-model="this.state.value"/>',
    },
    {
        "name": "simple t-esc",
        "content": '<div><t t-esc="coucou"/></div>',
        "expected": '<div><t t-esc="this.coucou"/></div>',
    },
    {
        "name": "t-tag",
        "content": '<t t-tag="v"/>',
        "expected": '<t t-tag="this.v"/>',
    },
    {
        "name": "comments",
        "content": "<div><!-- dfsf --></div>",
        "expected": "<div><!-- dfsf --></div>",
    },
    # TODO, not super important
    #     {
    #         "name": "comments 2",
    #         "content": """<?xml version="1.0" encoding="UTF-8"?>
    # <!--This field displays a placeholder even if the field is currently not selected.-->
    # <templates xml:space="preserve">
    # </templates>
    # """,
    #         "expected": """<?xml version="1.0" encoding="UTF-8"?>
    # <!--This field displays a placeholder even if the field is currently not selected.-->
    # <templates xml:space="preserve">
    # </templates>
    # """,
    #     },

    {
        "name": "simple t-out",
        "content": '<div><t t-out="coucou"/></div>',
        "expected": '<div><t t-out="this.coucou"/></div>',
    },
    {
        "name": "some encoding thing",
        "content": """<div t-esc="display || '&#8203;'"/>""",
        "expected": """<div t-esc="this.display || '&#8203;'"/>""",
    },
    {
        "name": "another t-out",
        "content": '<div><t t-out="coucou.truc"/></div>',
        "expected": '<div><t t-out="this.coucou.truc"/></div>',
    },
    {
        "name": "t-att",
        "content": '<div t-att="attributes"/>',
        "expected": '<div t-att="this.attributes"/>',
    },
    {
        "name": "simple t-attf-class",
        "content": '<div t-attf-class="abc#{d}ef"/>',
        "expected": '<div t-attf-class="abc#{this.d}ef"/>',
    },
    {
        "name": "another t-attf-class",
        "content": '<div t-attf-class="abc#{ d }ef"/>',
        "expected": '<div t-attf-class="abc#{ this.d }ef"/>',
    },
    {
        "name": "t-att-class object syntax",
        "content": """<div t-att-class="{'a': v}"/>""",
        "expected": """<div t-att-class="{'a': this.v}"/>""",
    },
    {
        "name": "t-att-class object syntax, variation",
        "content": """<div t-att-class="{a: v}"/>""",
        "expected": """<div t-att-class="{a: this.v}"/>""",
    },
    {
        "name": "t-att-class object syntax, variation2",
        "content": """<div t-att-class="{a: v, b: u}"/>""",
        "expected": """<div t-att-class="{a: this.v, b: this.u}"/>""",
    },
    {
        "name": "t-on-click",
        "content": '<div t-on-click="onClick"/>',
        "expected": '<div t-on-click="this.onClick"/>',
    },
    {
        "name": "short object notation",
        "content": '<C t-props="{ a }"/>',
        "expected": '<C t-props="{ a: this.a }"/>',
    },
    {
        "name": "short object notation, 2",
        "content": '<C t-props="{ a, b }"/>',
        "expected": '<C t-props="{ a: this.a, b: this.b }"/>',
    },
    {
        "name": "short object notation, 3",
        "content": '<C t-props="{ a, b, c }"/>',
        "expected": '<C t-props="{ a: this.a, b: this.b, c: this.c }"/>',
    },
    {
        "name": "short object notation, 3",
        "content": '<C t-props="{ a, b: this.u, c }"/>',
        "expected": '<C t-props="{ a: this.a, b: this.u, c: this.c }"/>',
    },
    {
        "name": "t-on-click.bind",
        "content": '<div t-on-click.bind="onClick"/>',
        "expected": '<div t-on-click.bind="this.onClick"/>',
    },
    {
        "name": "t-custom-model",
        "content": '<input t-custom-model="state.name"/>',
        "expected": '<input t-custom-model="this.state.name"/>',
    },
    {
        "name": "t-custom-model modifier",
        "content": '<input t-custom-model.trim="state.name"/>',
        "expected": '<input t-custom-model.trim="this.state.name"/>',
    },
    {
        "name": "t-portal",
        "content": '<div t-portal="portalTarget"/>',
        "expected": '<div t-portal="this.portalTarget"/>',
    },
    {
        "name": "t-custom-portal",
        "content": '<div t-custom-portal="portalTarget"/>',
        "expected": '<div t-custom-portal="this.portalTarget"/>',
    },
    {
        "name": "t-ref",
        "content": """<input t-ref="{{state.activePageId === page.id ? 'autofocus' : page.id}}"/>""",
        "expected": """<input t-ref="{{this.state.activePageId === this.page.id ? 'autofocus' : this.page.id}}"/>""",
    },
    {
        "name": "t-custom-ref",
        "content": """<input t-custom-ref="root"/>""",
        "expected": """<input t-custom-ref="root"/>""",
    },
    {
        "name": "t-custom-ref dynamic",
        "content": """<input t-custom-ref="{{state.activePageId === page.id ? 'autofocus' : page.id}}"/>""",
        "expected": """<input t-custom-ref="{{this.state.activePageId === this.page.id ? 'autofocus' : this.page.id}}"/>""",
    },
    {
        "name": "formatting",
        "content": """<A onSaveCallback="(this.timesheet) =&gt; this.onSaveTimesheetForm(this.timesheet)"/>""",
        "expected": """<A onSaveCallback="(this.timesheet) => this.onSaveTimesheetForm(this.timesheet)"/>""",
    },
    {
        "name": "Arrow detection with &gt",
        "content": """<A onSaveCallback="(timesheet, changes) =&gt; this.onSaveTimesheetForm(timesheet, changes)"/>""",
        "expected": """<A onSaveCallback="(timesheet, changes) => this.onSaveTimesheetForm(timesheet, changes)"/>""",
    },
    {
        "name": "t-if",
        "content": '<div t-if="expr">aa</div>',
        "expected": '<div t-if="this.expr">aa</div>',
    },
    {
        "name": "t-if",
        "content": '<div t-if="a or b gt c">aa</div>',
        "expected": '<div t-if="this.a or this.b gt this.c">aa</div>',
    },
    {
        "name": "keep leading and trailing whitespaces",
        "content": '''<div t-out="
            a
        ">aa</div>''',
        "expected": '''<div t-out="
            this.a
        ">aa</div>''',
    },
    {
        "name": "keep leading and trailing whitespaces in t-attf-",
        "content": '''<div t-attf-style="background-color: {{
            color
        }}; border: {{     border     }}">aa</div>''',
        "expected": '''<div t-attf-style="background-color: {{
            this.color
        }}; border: {{     this.border     }}">aa</div>''',
    },
    {
        "name": "simple xpath",
        "content": """
<t t-name="sfsdg" t-inherit="web.ListView">
<xpath expr="//t[@t-if='state.printItems.length']/Dropdown"/>
</t>
""",
        "expected": """
<t t-name="sfsdg" t-inherit="web.ListView">
<xpath expr="//t[@t-if='this.state.printItems.length']/Dropdown"/>
</t>
""",
    },
    {
        "name": "simple xpath 2",
        "content": """<xpath expr="./div[@t-ref='root']" />""",
        "expected": """<xpath expr="./div[@t-ref='root']" />""",
    },
    {
        "name": "simple xpath 3",
        "content": """<xpath expr="//t[@t-slot='default']"/>""",
        "expected": """<xpath expr="//t[@t-slot='default']"/>""",
    },
    {
        "name": "simple xpath 4",
        "content": """<xpath expr="//Layout/t[@t-set-slot='control-panel-actions']" position="replace"/>""",
        "expected": """<xpath expr="//Layout/t[@t-set-slot='control-panel-actions']" position="replace"/>""",
    },
    {
        "name": "simple xpath 5, t-call",
        "content": """<t t-name="sfsdg" t-inherit="web.ListView"><xpath expr="//*[@t-call='web.StatusBarField.Dropdown']" /></t>""",
        "expected": """<t t-name="sfsdg" t-inherit="web.ListView"><xpath expr="//*[@t-call='web.StatusBarField.Dropdown']" /></t>""",
    },
    {
        "name": "simple xpath 5, t-call dynamic",
        "content": """<t t-name="sfsdg" t-inherit="web.ListView"><xpath expr="//*[@t-call='{{a}}']" /></t>""",
        "expected": """<t t-name="sfsdg" t-inherit="web.ListView"><xpath expr="//*[@t-call='{{this.a}}']" /></t>""",
    },
    {
        "name": "xpath position=attribute",
        "content": """
<t t-name="sfsdg" t-inherit="web.ListView">
<xpath expr="//div[hasclass('o_cp_action_menus')]" position="attributes">
    <attribute name="t-if">env.isSmall or hasItems</attribute>
</xpath>
</t>
""",
        "expected": """
<t t-name="sfsdg" t-inherit="web.ListView">
<xpath expr="//div[hasclass('o_cp_action_menus')]" position="attributes">
    <attribute name="t-if">this.env.isSmall or this.hasItems</attribute>
</xpath>
</t>
""",
    },
    {
        "name": "attribute in xpath",
        "content": """
<t t-name="sfsdg" t-inherit="web.ListView">
<xpath expr="//button[@class='nav-link']" position="attributes">
    <attribute name="t-on-click">() => changeTabTo(navItem[0])</attribute>
</xpath>
</t>
""",
        "expected": """
<t t-name="sfsdg" t-inherit="web.ListView">
<xpath expr="//button[@class='nav-link']" position="attributes">
    <attribute name="t-on-click">() => this.changeTabTo(this.navItem[0])</attribute>
</xpath>
</t>
""",
    },
    {
        "name": "attributes targetting through component",
        "content": """
<t t-name="sfsdg" t-inherit="web.ListView">
<xpath expr="//Dropdown/button" position="attributes">
    <attribute name="class" remove="p-0" add="shadow-none" separator=" "/>
    <attribute name="t-att-class">getTogglerClass(currentValue)</attribute>
</xpath>
</t>
""",
        "expected": """
<t t-name="sfsdg" t-inherit="web.ListView">
<xpath expr="//Dropdown/button" position="attributes">
    <attribute name="class" remove="p-0" add="shadow-none" separator=" "/>
    <attribute name="t-att-class">this.getTogglerClass(this.currentValue)</attribute>
</xpath>
</t>
""",
    },
    {
        "name": "xpath position=attribute, 2",
        "content": """
<t t-name="sfsdg" t-inherit="web.ListView">
<xpath expr="//div[hasclass('o_cp_action_menus')]" position="attributes">
    <attribute name="t-on-click">onClick</attribute>
</xpath>
</t>
""",
        "expected": """
<t t-name="sfsdg" t-inherit="web.ListView">
<xpath expr="//div[hasclass('o_cp_action_menus')]" position="attributes">
    <attribute name="t-on-click">this.onClick</attribute>
</xpath>
</t>
""",
    },
    {
        "name": "xpath position=attribute, variation",
        "content": """
<t t-name="project.ProjectTaskKanbanRenderer" t-inherit="web.KanbanRenderer" t-inherit-mode="primary">
    <xpath expr="//div[hasclass('o_kanban_group_nocontent')]" position="attributes">
        <attribute name="t-if">props.list.groups.length === 0 &amp;&amp; !props.hideKanbanStagesNocontent</attribute>
    </xpath>
</t>
""",
        "expected": """
<t t-name="project.ProjectTaskKanbanRenderer" t-inherit="web.KanbanRenderer" t-inherit-mode="primary">
    <xpath expr="//div[hasclass('o_kanban_group_nocontent')]" position="attributes">
        <attribute name="t-if">this.props.list.groups.length === 0 &amp;&amp; !this.props.hideKanbanStagesNocontent</attribute>
    </xpath>
</t>
""",
    },
    {
        "name": "xpath position=attribute, add and remove",
        "content": """
<t t-name="mail.RottingStatusBarDurationField" t-inherit="mail.StatusBarDurationField" t-inherit-mode="primary">
    <xpath expr="//span[@t-att-title='item.fullTimeInStage']" position="attributes">
        <attribute name="t-attf-class" add="--o-mail-livechat-btn-color {{ props.thread?.channel?.channel_type === 'ai_chat' ? 'ms-0' : '' }}" separator=" "/>
        <attribute name="t-if" remove="(!props.record.data.is_rotting || !item.isSelected)" separator=" and "/>
        <attribute name="t-if" add="props.record.data" remove="!item.isSelected" separator=" and "/>
    </xpath>
</t>
""",
        "expected": """
<t t-name="mail.RottingStatusBarDurationField" t-inherit="mail.StatusBarDurationField" t-inherit-mode="primary">
    <xpath expr="//span[@t-att-title='this.item.fullTimeInStage']" position="attributes">
        <attribute name="t-attf-class" add="--o-mail-livechat-btn-color {{ this.props.thread?.channel?.channel_type === 'ai_chat' ? 'ms-0' : '' }}" separator=" "/>
        <attribute name="t-if" remove="(!this.props.record.data.is_rotting || !this.item.isSelected)" separator=" and "/>
        <attribute name="t-if" add="this.props.record.data" remove="!this.item.isSelected" separator=" and "/>
    </xpath>
</t>
""",
    },
    {
        "name": "t-slot scope",
        "content": """
<WithSearch t-props="withSearchProps" t-slot-scope="search">
    <t t-component="Controller"
        t-on-click="handleActionLinks"
        t-props="componentProps"
        context="search.context"
        domain="search.domain"
        groupBy="search.groupBy"
        orderBy="search.orderBy"
        display="search.display"/>
</WithSearch>
""",
        "expected": """
<WithSearch t-props="this.withSearchProps" t-slot-scope="search">
    <t t-component="this.Controller"
        t-on-click="this.handleActionLinks"
        t-props="this.componentProps"
        context="search.context"
        domain="search.domain"
        groupBy="search.groupBy"
        orderBy="search.orderBy"
        display="search.display"/>
</WithSearch>
""",
    },
    {
        "name": "t-slot props",
        "content": """
            <t>
                <t t-set="b" t-value="'b'"/>
                <t t-call-slot="default" a="a" b="b"/>
            </t>
        """,
        "expected": """
            <t>
                <t t-set="b" t-value="'b'"/>
                <t t-call-slot="default" a="this.a" b="b"/>
            </t>
        """,
    },
    {
        "name": "t-call-slot props",
        "content": """
            <t>
                <t t-set="b" t-value="'b'"/>
                <t t-call-slot="default" a="a" b="b"/>
            </t>
        """,
        "expected": """
            <t>
                <t t-set="b" t-value="'b'"/>
                <t t-call-slot="default" a="this.a" b="b"/>
            </t>
        """,
    },
    {
        "name": "t-call inline params",
        "content": """
            <t>
                <t t-call="web.SectionMenu" section="subSection" isNested="true"/>
            </t>
        """,
        "expected": """
            <t>
                <t t-call="web.SectionMenu" section="this.subSection" isNested="true"/>
            </t>
        """,
    },
    {
        "name": "t-call inline params with .translate",
        "content": """
            <t>
                <t t-call="web.SectionMenu" section="subSection" title.translate="Open leads"/>
            </t>
        """,
        "expected": """
            <t>
                <t t-call="web.SectionMenu" section="this.subSection" title.translate="Open leads"/>
            </t>
        """,
    },
    {
        "name": "t-call inside t-inherit (xpath directives)",
        "content": """
            <t t-name="account.ProductCatalogSearchPanel" t-inherit="web.SearchPanel" t-inherit-mode="primary">
                <t t-call="web.SearchPanel.Regular" position="attributes">
                    <attribute name="t-call">account.ProductCatalogSearchPanelContent</attribute>
                </t>
            </t>
        """,
        "expected": """
            <t t-name="account.ProductCatalogSearchPanel" t-inherit="web.SearchPanel" t-inherit-mode="primary">
                <t t-call="web.SearchPanel.Regular" position="attributes">
                    <attribute name="t-call">account.ProductCatalogSearchPanelContent</attribute>
                </t>
            </t>
        """,
    },
    {
        "name": "t-key",
        "content": '<div t-key="expr">aa</div>',
        "expected": '<div t-key="this.expr">aa</div>',
    },
    {"name": "component", "content": '<A b="c"/>', "expected": '<A b="this.c"/>'},
    {
        "name": "component with props translage",
        "content": '<A b.translate="c"/>',
        "expected": '<A b.translate="c"/>',
    },
    {
        "name": "t-component",
        "content": '<t t-component="C" b="c"/>',
        "expected": '<t t-component="this.C" b="this.c"/>',
    },
    {
        "name": "component, variation",
        "content": '<A b="(s) ? 1 : 2"/>',
        "expected": '<A b="(this.s) ? 1 : 2"/>',
    },
    {
        "name": "component postion attribute",
        "content": """
<t t-name="a"> <A position="replace"/> <t t-name="c" t-inherit="b" t-inherit-mode="primary"> <A position="replace"/> </t> </t>
""",
        "expected": """
<t t-name="a"> <A position="this.replace"/> <t t-name="c" t-inherit="b" t-inherit-mode="primary"> <A position="replace"/> </t> </t>
""",
    },
    {
        "name": "component, another variation",
        "content": """
<MessageInReply t-if="this.message.parent_id" class="'mx-2 p-1 pb-0 ' + (this.showTextVisually ? 'mt-1' : 'my-1')" message="this.message" onClick="this.props.onParentMessageClick"/>
""",
        "expected": """
<MessageInReply t-if="this.message.parent_id" class="'mx-2 p-1 pb-0 ' + (this.showTextVisually ? 'mt-1' : 'my-1')" message="this.message" onClick="this.props.onParentMessageClick"/>
""",
    },

    {
        "name": "t-on-keydown",
        "content": '<div t-on-keydown="onKeydown"/>',
        "expected": '<div t-on-keydown="this.onKeydown"/>',
    },
    {
        "name": "event handler with ev",
        "content": '<div t-on-pointerdown="(ev) => this.onOptionPointerDown(option, ev)"/>',
        "expected": '<div t-on-pointerdown="(ev) => this.onOptionPointerDown(this.option, ev)"/>',
    },
    {
        "name": "event handler with ev, variation",
        "content": '<div t-on-pointerdown="ev => this.onOptionPointerDown(option, ev)"/>',
        "expected": '<div t-on-pointerdown="ev => this.onOptionPointerDown(this.option, ev)"/>',
    },
    {
        "name": "event handler with ev, variation 2",
        "content": """
<t t-inherit="resource_mail.Many2OneAvatarResourceField" t-inherit-mode="extension">
    <xpath expr="//span[hasclass('o_material_resource')]" position="attributes">
        <attribute name="t-on-click.stop">(ev) => this.openMaterialPopover(ev.currentTarget)</attribute>
    </xpath>
</t>""",
        "expected": """
<t t-inherit="resource_mail.Many2OneAvatarResourceField" t-inherit-mode="extension">
    <xpath expr="//span[hasclass('o_material_resource')]" position="attributes">
        <attribute name="t-on-click.stop">(ev) => this.openMaterialPopover(ev.currentTarget)</attribute>
    </xpath>
</t>""",
    },
    {
        "name": "t-att-title",
        "content": '<div t-att-title="v"/>',
        "expected": '<div t-att-title="this.v"/>',
    },
    {
        "name": "t-att-class",
        "content": """<div t-att-class="{'a': a + b}"/>""",
        "expected": """<div t-att-class="{'a': this.a + this.b}"/>""",
    },
    {
        "name": "t-elif",
        "content": '<div t-elif="a"/>',
        "expected": '<div t-elif="this.a"/>',
    },
    {
        "name": "t-attf",
        "content": """<div t-attf-id="aaa{{props.id or 'autocomplete'}}_{{source_index}}_loading"/>""",
        "expected": """<div t-attf-id="aaa{{this.props.id or 'autocomplete'}}_{{this.source_index}}_loading"/>""",
    },
    {
        "name": "simple t-set",
        "content": """
<div>
  <t t-set="a" t-value="b"/>
  <t t-out="a"/>
  <t t-out="b"/>
</div>
""",
        "expected": """
<div>
  <t t-set="a" t-value="this.b"/>
  <t t-out="a"/>
  <t t-out="this.b"/>
</div>
""",
    },
    {
        "name": "t foreach",
        "content": """
<t t-foreach="items" t-as="item" t-key="item.id">
    <div><t t-out="item.value"/></div>
</t>
""",
        "expected": """
<t t-foreach="this.items" t-as="item" t-key="item.id">
    <div><t t-out="item.value"/></div>
</t>
""",
    },
    {
        "name": "xml do not transform &apos;",
        "content": """
<templates>
    <t t-name="knowledge.MacrosEmbeddedClipboard" t-inherit="knowledge.EmbeddedClipboard" t-inherit-mode="primary">
         <xpath expr='//EmbeddedComponentToolbarButton[@name="&apos;copyToClipboard&apos;"]' position="before">
            <EmbeddedComponentToolbarButton
                hidden="!targetRecordInfo?.canPostMessages"
                icon="'fa-envelope'"
                label.translate="Send as Message"
                onClick.bind="onClickSendAsMessage"
            />
            <EmbeddedComponentToolbarButton
                hidden="!targetRecordInfo?.withHtmlField"
                icon="'fa-pencil-square'"
                label="htmlFieldTargetMessage"
                onClick.bind="onClickUseAsDescription"
            />
        </xpath>
    </t>
</templates>
""",
        "expected": """
<templates>
    <t t-name="knowledge.MacrosEmbeddedClipboard" t-inherit="knowledge.EmbeddedClipboard" t-inherit-mode="primary">
         <xpath expr='//EmbeddedComponentToolbarButton[@name="&apos;copyToClipboard&apos;"]' position="before">
            <EmbeddedComponentToolbarButton
                hidden="!this.targetRecordInfo?.canPostMessages"
                icon="'fa-envelope'"
                label.translate="Send as Message"
                onClick.bind="this.onClickSendAsMessage"
            />
            <EmbeddedComponentToolbarButton
                hidden="!this.targetRecordInfo?.withHtmlField"
                icon="'fa-pencil-square'"
                label="this.htmlFieldTargetMessage"
                onClick.bind="this.onClickUseAsDescription"
            />
        </xpath>
    </t>
</templates>
""",
    },
    {
        "name": "Arrow function formatting error",
        "content": """<button t-on-click= "(e) => this.removeLine(line,e)"/>""",
        "expected": """<button t-on-click="(e) => this.removeLine(this.line,e)"/>""",
    },
    {
        "name": "Doesn't but this before &...; expr",
        "content": """
<div t-att-class="account?.balance &lt; 0 ? 'text-danger' : ''" t-out="formattedBalance(account)"/>
""",
        "expected": """
<div t-att-class="this.account?.balance &lt; 0 ? 'text-danger' : ''" t-out="this.formattedBalance(this.account)"/>
""",
    },
    {
        "name": " Add this to t-set-slot params",
        "content": """
<t t-set-slot="stand_number" route="`/pos-self/${selfOrder.config.id}/stand_number`">
    <StandNumberPage />
</t>
""",
        "expected": """
<t t-set-slot="stand_number" route="`/pos-self/${this.selfOrder.config.id}/stand_number`">
    <StandNumberPage />
</t>
""",
    },
    {
        # t-as="state" in a t-foreach pollutes bound_variables for the whole template,
        # preventing state.x from being rewritten to this.state.x outside the loop.
        "name": "t-as name shadows component state outside its scope",
        "content": """
<t t-name="foo">
    <input t-custom-model="state.name"/>
    <t t-foreach="items" t-as="state" t-key="state.id"/>
</t>
""",
        "expected": """
<t t-name="foo">
    <input t-custom-model="this.state.name"/>
    <t t-foreach="this.items" t-as="state" t-key="state.id"/>
</t>
""",
    },
    # TODO, not super important
    #     {
    #         "name": "xml formatting error",
    #         "content": """
    # <templates>
    #     <t t-name="knowledge.MacrosEmbeddedClipboard" t-inherit="knowledge.EmbeddedClipboard" t-inherit-mode="primary">
    #         <CardLayout fromTrialMode="this.props.fromTrialMode" companyImageUrl="this.companyImageUrl" kioskReturn.bind="kioskReturn" activeDisplay = "this.state.active_display"/>
    #     </t>
    # </templates>
    # """,
    #         "expected": """
    # <templates>
    #     <t t-name="knowledge.MacrosEmbeddedClipboard" t-inherit="knowledge.EmbeddedClipboard" t-inherit-mode="primary">
    #         <CardLayout fromTrialMode="this.props.fromTrialMode" companyImageUrl="this.companyImageUrl" kioskReturn.bind="kioskReturn" activeDisplay = "this.state.active_display"/>
    #     </t>
    # </templates>
    # """,
    #     },
    {
        "name": "t foreach, with variables",
        "content": """
<t t-foreach="items" t-as="item" t-key="item.id">
    <div><t t-out="item.value"/></div>
    <div><t t-out="item_value"/></div>
    <div><t t-out="item_index"/></div>
    <div><t t-out="item_first"/></div>
    <div><t t-out="item_last"/></div>
    <div><t t-out="item_blip"/></div>
</t>
""",
        "expected": """
<t t-foreach="this.items" t-as="item" t-key="item.id">
    <div><t t-out="item.value"/></div>
    <div><t t-out="item_value"/></div>
    <div><t t-out="item_index"/></div>
    <div><t t-out="item_first"/></div>
    <div><t t-out="item_last"/></div>
    <div><t t-out="this.item_blip"/></div>
</t>
""",
    },
    {
        "name": "t component and t-props",
        "content": '<t t-component="comp" t-props="getProps()"/>',
        "expected": '<t t-component="this.comp" t-props="this.getProps()"/>',
    },
    {
        "name": "more complex expression",
        "content": """
<t t-foreach="this.tabs" t-as="tab" t-key="tab.id">
    <button t-attf-class="btn btn-sm text-truncate btn-tab #{tab.id}-tab #{ isDarkTheme ? 'btn-secondary' : 'btn-light'} #{state.activeTab === tab.id ? 'active' : ''}"
        t-on-click="() => this.setTab(tab.id)">
        <t t-out="tab.name" />
    </button>
</t>
""",
        "expected": """
<t t-foreach="this.tabs" t-as="tab" t-key="tab.id">
    <button t-attf-class="btn btn-sm text-truncate btn-tab #{tab.id}-tab #{ this.isDarkTheme ? 'btn-secondary' : 'btn-light'} #{this.state.activeTab === tab.id ? 'active' : ''}"
        t-on-click="() => this.setTab(tab.id)">
        <t t-out="tab.name" />
    </button>
</t>
""",
    },
    {
        "name": "random template",
        "content": """
<t t-foreach="sources" t-as="source" t-key="source.id">
    <t t-foreach="source.options" t-as="option" t-key="option.id">
        <li
            class="o-autocomplete--dropdown-item ui-menu-item d-block"
            t-att-class="option.cssClass"
            t-on-mouseenter="() => this.onOptionMouseEnter([source_index, option_index])"
            t-on-mouseleave="() => this.onOptionMouseLeave([source_index, option_index])"
            t-on-click="() => this.onOptionClick(option)"
            t-on-pointerdown="(ev) => this.onOptionPointerDown(option, ev)"
        >
            <t t-tag="option.unselectable ? 'span' : 'a'"
                class="dropdown-item ui-menu-item-wrapper text-truncate"
                t-attf-id="{{props.id or 'autocomplete'}}_{{source_index}}_{{option_index}}"
                t-att-role="!option.unselectable and 'option'"
                t-att-href="!option.unselectable and '#'"
                t-att-class="{ 'ui-state-active': isActiveSourceOption([source_index, option_index]) }"
                t-att-aria-selected="isActiveSourceOption([source_index, option_index]) ? 'true' : 'false'"
            >
                <t t-slot="{{ source.optionSlot }}" label="option.label" data="option.data">
                    <t t-if="!option.labelTermOrder" t-out="option.label"/>
                    <t t-else="">
                        <t t-foreach="option.labelTermOrder.labelBits" t-as="bit" t-key="bit.id">
                            <t t-if="!option.labelTermOrder.searchTermIndexes.includes(bit.id)" t-esc="bit.bit"/>
                            <mark t-else="" class="o-autocomplete--mark" t-esc="bit.bit"/>
                        </t>
                    </t>
                </t>
            </t>
        </li>
    </t>
</t>
""",
        "expected": """
<t t-foreach="this.sources" t-as="source" t-key="source.id">
    <t t-foreach="source.options" t-as="option" t-key="option.id">
        <li
            class="o-autocomplete--dropdown-item ui-menu-item d-block"
            t-att-class="option.cssClass"
            t-on-mouseenter="() => this.onOptionMouseEnter([source_index, option_index])"
            t-on-mouseleave="() => this.onOptionMouseLeave([source_index, option_index])"
            t-on-click="() => this.onOptionClick(option)"
            t-on-pointerdown="(ev) => this.onOptionPointerDown(option, ev)"
        >
            <t t-tag="option.unselectable ? 'span' : 'a'"
                class="dropdown-item ui-menu-item-wrapper text-truncate"
                t-attf-id="{{this.props.id or 'autocomplete'}}_{{source_index}}_{{option_index}}"
                t-att-role="!option.unselectable and 'option'"
                t-att-href="!option.unselectable and '#'"
                t-att-class="{ 'ui-state-active': this.isActiveSourceOption([source_index, option_index]) }"
                t-att-aria-selected="this.isActiveSourceOption([source_index, option_index]) ? 'true' : 'false'"
            >
                <t t-slot="{{ source.optionSlot }}" label="option.label" data="option.data">
                    <t t-if="!option.labelTermOrder" t-out="option.label"/>
                    <t t-else="">
                        <t t-foreach="option.labelTermOrder.labelBits" t-as="bit" t-key="bit.id">
                            <t t-if="!option.labelTermOrder.searchTermIndexes.includes(bit.id)" t-esc="bit.bit"/>
                            <mark t-else="" class="o-autocomplete--mark" t-esc="bit.bit"/>
                        </t>
                    </t>
                </t>
            </t>
        </li>
    </t>
</t>
""",
    },
    {
        "name": "mail message component",
        "content": """
    <t t-name="mail.Message">
        <ActionSwiper onRightSwipe="onRightSwipe">
            <t t-set="dummy" t-value="computeActions()"/>
            <div class="o-mail-Message position-relative rounded-0 bg-inherit"
                t-att-data-starred="message.starred"
                t-att-data-persistent="message.persistent"
                t-att-class="attClass"
                role="group"
                t-att-aria-label="messageTypeText"
                t-on-click="onClick"
                t-on-contextmenu="onContextMenu"
                t-on-mouseenter="onMouseenter"
                t-on-mouseleave="onMouseleave"
                t-ref="root"
                t-if="message.exists()"
            >
                <MessageContextMenu anchorRef="rightClickAnchor" dropdownState="rightClickDropdownState" message="message" thread="props.thread"/>
                <div class="o-mail-Message-jumpTarget position-absolute top-0 pe-none"/>
                <div t-if="props.asCard and isMobileOS" class="position-absolute end-0 z-1 m-n2"><t t-call="mail.Message.actions"/></div>
                <div class="o-mail-Message-core position-relative d-flex flex-shrink-0 bg-inherit">
                    <div class="o-mail-Message-sidebar d-flex flex-shrink-0 align-items-center flex-column bg-inherit" t-att-class="{ 'align-items-start': !isAlignedRight, 'o-inChatWindow': env.inChatWindow }">
                        <t t-if="!props.squashed">
                            <div class="o-mail-Message-avatarContainer position-relative bg-inherit rounded-3" t-att-class="getAvatarContainerAttClass()">
                                <img class="o-mail-Message-avatar w-100 h-100 rounded-3" t-att-src="authorAvatarUrl" t-att-class="authorAvatarAttClass"/>
                            </div>
                            <t t-if="message.starred" t-call="mail.Message.sidebarStarred"/>
                        </t>
                        <t t-elif="message.isPending" t-call="mail.Message.pendingStatus"/>
                        <t t-elif="!message.is_transient">
                            <small t-if="isActive and props.showDates" class="o-mail-Message-date o-xsmaller mt-2 text-center lh-1" t-att-title="message.datetimeShort">
                                <t t-esc="message.dateSimple"/>
                            </small>
                            <t t-elif="message.starred" t-call="mail.Message.sidebarStarred"/>
                        </t>
                    </div>
                    <div class="w-100 o-min-width-0" t-att-class="{ 'flex-grow-1': isEditing }" t-ref="messageContent">
                        <div t-if="!props.squashed" class="o-mail-Message-header d-flex flex-wrap align-items-baseline lh-1" t-att-class="{ 'mb-1': !message.isNote, 'pe-2': props.asCard and isMobileOS }" name="header">
                            <span t-if="message.authorName and shouldDisplayAuthorName" class="o-mail-Message-author smaller" t-att-class="getAuthorAttClass()">
                                <strong class="me-1 o-fw-600" t-esc="message.authorName"/>
                            </span>
                            <t t-if="!isAlignedRight" t-call="mail.Message.notification"/>
                            <t t-if="isAlignedRight and !message.bubbleColor and !(props.asCard and isMobileOS)" t-call="mail.Message.actions"/>
                            <small t-if="!message.is_transient" class="o-mail-Message-date o-xsmaller" t-att-title="message.datetimeShort">
                                <t t-if="message.isPending" t-call="mail.Message.pendingStatus"/>
                                <t t-else="" t-out="message.dateSimpleWithDay"/>
                            </small>
                            <small t-if="isPersistentMessageFromAnotherThread" t-on-click.prevent="openRecord" class="ms-1 text-500">
                                <t t-if="message.channel_id">
                                    (from <a t-att-href="message.resUrl"><t t-esc="message.thread.prefix"/><t t-esc="message.channel_id.displayName or message.default_subject"/></a>)
                                </t>
                                <t t-else="">
                                    on <a t-if="message.thread.displayName" t-att-href="message.resUrl" t-esc="message.thread.displayName"/><em class="pe-1 text-decoration-line-through" t-else="">Deleted document</em>
                                </t>
                            </small>
                            <div t-if="props.message.scheduledDatetime" t-att-class="{ 'ms-2': (env.inChatWindow and isAlignedRight) or (isPersistentMessageFromAnotherThread) }" t-att-title="props.message.scheduledDateSimple">
                                <span class="text-600 cursor-pointer">
                                    <i class="fa fa-calendar-o"/>
                                </span>
                            </div>
                            <t t-if="isAlignedRight" t-call="mail.Message.notification"/>
                            <t t-if="!isAlignedRight and !message.bubbleColor and !(props.asCard and isMobileOS)" t-call="mail.Message.actions"/>
                        </div>
                        <div class="o-mail-Message-contentContainer position-relative d-flex" t-att-class="{ 'flex-row-reverse': isAlignedRight }">
                            <div class="o-mail-Message-content o-min-width-0" t-att-class="{ 'w-100': isEditing, 'opacity-50': message.isPending, 'pt-1': message.isNote, 'o-mail-Message-pollContent flex-grow-1': message.poll }">
                                <div class="o-mail-Message-textContent position-relative d-flex" t-att-class="{ 'w-100': isEditing }">
                                    <t t-set="showTextVisually" t-value="!message.linkPreviewSquash and (message.hasTextContent or message.subtype_id?.description or message.isEmpty)"/>
                                    <t t-if="message.message_type === 'notification' and message.richBody" t-call="mail.Message.bodyAsNotification" name="bodyAsNotification"/>
                                    <t t-if="message.isEmpty or (message.message_type !== 'notification' and !message.is_transient and (message.hasTextContent or message.subtype_id?.description or isEditing or message.parent_id))">
                                        <MessageLinkPreviewList t-if="!isEditing and message.linkPreviewSquash and !message.parent_id" messageLinkPreviews="message.message_link_preview_ids"/>
                                        <t t-else="">
                                            <div t-if="message.bubbleColor and !props.squashed" class="o-mail-Message-bubbleTail position-absolute d-flex" t-att-style="isAlignedRight ? 'right: -4px; transform: rotateY(180deg);' : 'left: -4px;'" t-att-class="{
                                                'o-blue': message.bubbleColor === 'blue',
                                                'o-green': message.bubbleColor === 'green',
                                                'o-orange': message.bubbleColor === 'orange',
                                            }">
                                                <svg viewBox="0 0 6 12" height="12" width="6" x="0px" y="0px">
                                                    <path class="o-mail-Message-bubbleTailBorder" fill="currentColor" d="M 0, 0 L 5, 9 V 0 z"/>
                                                    <path class="o-mail-Message-bubbleTailBg" fill="currentColor" d="M 2, 1 L 5, 7 V 1 z"/>
                                                </svg>
                                            </div>
                                            <div class="position-relative overflow-x-auto overflow-y-hidden d-inline-block o-discuss-text-body" t-att-class="{
                                                'w-100': isEditing,
                                                'o-rounded-bubble': message.bubbleColor and props.squashed,
                                                'o-rounded-bottom-bubble': message.bubbleColor and !props.squashed,
                                                'o-rounded-start-bubble': message.bubbleColor and !props.squashed and isAlignedRight,
                                                'o-rounded-end-bubble': message.bubbleColor and !props.squashed and !isAlignedRight,
                                            }">
                                                <div t-if="message.bubbleColor" class="o-mail-Message-bubble position-absolute top-0 start-0 w-100 h-100 border" t-att-class="{
                                                    'o-rounded-bubble': props.squashed,
                                                    'o-rounded-bottom-bubble': !props.squashed,
                                                    'o-rounded-start-bubble': !props.squashed and isAlignedRight,
                                                    'o-rounded-end-bubble': !props.squashed and !isAlignedRight,
                                                    'o-blue': message.bubbleColor === 'blue',
                                                    'o-green': message.bubbleColor === 'green',
                                                    'o-orange': message.bubbleColor === 'orange',
                                                }"/>
                                                <MessageInReply t-if="message.parent_id" class="'mx-2 p-1 pb-0 ' + (showTextVisually ? 'mt-1' : 'my-1')" message="message" onClick="props.onParentMessageClick"/>
                                                <div class="position-relative text-break o-mail-Message-body" t-att-class="{
                                                            'p-1': message.isNote,
                                                            'fs-1': !isEditing and !env.inChatter and message.onlyEmojis,
                                                            'mb-0': !message.isNote,
                                                            'py-2': !message.isNote and !isEditing and showTextVisually,
                                                            'pt-2 pb-1': !message.isNote and isEditing,
                                                            'o-note': message.isNote,
                                                            'o-rounded-bubble': props.squashed,
                                                            'align-self-start o-rounded-end-bubble o-rounded-bottom-bubble': !isEditing and !message.isNote and !props.squashed,
                                                            'flex-grow-1': isEditing,
                                                            }" t-ref="body">
                                                    <i t-if="message.isEmpty" class="text-muted opacity-75" t-out="message.inlineBody"/>
                                                    <Composer t-elif="isEditing" autofocus="true" composer="message.composer" onDiscardCallback.bind="exitEditMode" onPostCallback.bind="exitEditMode" mode="'compact'" sidebar="false"/>
                                                    <t t-else="">
                                                        <em t-if="message.subject and !message.isSubjectSimilarToThreadName and !message.isSubjectDefault" class="d-block text-muted smaller">Subject: <t t-out="props.messageSearch?.highlight(message.subject) ?? message.subject"/></em>
                                                        <div class="overflow-x-auto" t-if="message.message_type and message.message_type.includes('email')" t-ref="shadowBody"/>
                                                        <t t-elif="message.showTranslation" t-out="message.richTranslationValue"/>
                                                        <div class="o-mail-Message-richBody overflow-x-auto" t-elif="message.hasTextContent and message.richBody and !message.linkPreviewSquash" t-out="props.messageSearch?.highlight(message.richBody) ?? message.richBody"/>
                                                        <p class="fst-italic text-muted small" t-if="message.showTranslation">
                                                            <t t-if="message.translationSource" t-esc="translatedFromText"/>
                                                        </p>
                                                        <p class="fst-italic text-muted small" t-if="message.translationErrors">
                                                            <i class="text-danger fa fa-warning" role="img" aria-label="Translation Failure"/>
                                                            <t t-if="message.translationErrors" t-esc="translationFailureText"/>
                                                        </p>
                                                        <t t-if="showSubtypeDescription" t-out="props.messageSearch?.highlight(message.subtype_id?.description) ?? message.subtype_id?.description"/>
                                                    </t>
                                                </div>
                                            </div>
                                        </t>
                                    </t>
                                    <t t-if="message.bubbleColor and message.hasTextContent and !env.inChatWindow and !(props.asCard and isMobileOS)" t-call="mail.Message.actions"/>
                                    <PollResult t-if="message.ended_poll_ids.length" poll="message.poll"/>
                                    <Poll t-elif="message.poll" poll="message.poll"/>
                                </div>
                                <div class="position-relative">
                                    <AttachmentList
                                        t-if="message.attachment_ids.length > 0"
                                        attachments="message.attachment_ids.map((a) => a)"
                                        unlinkAttachment.bind="onClickAttachmentUnlink"
                                        messageSearch="props.messageSearch"/>
                                </div>
                                <MessageLinkPreviewList t-if="(message.message_link_preview_ids.length > 0 and store.hasLinkPreviewFeature and !message.linkPreviewSquash) or (!isEditing and message.linkPreviewSquash and message.parent_id)" messageLinkPreviews="message.message_link_preview_ids"/>
                            </div>
                            <t t-if="message.bubbleColor and (!message.hasTextContent or env.inChatWindow) and !(props.asCard and isMobileOS)" t-call="mail.Message.actions"/>
                        </div>
                        <MessageReactions message="message" openReactionMenu="openReactionMenu" t-if="message.reactions.length"/>
                        <t name="after-reactions"/>
                    </div>
                </div>
            </div>
        </ActionSwiper>
    </t>
    """,
        "expected": """
    <t t-name="mail.Message">
        <ActionSwiper onRightSwipe="this.onRightSwipe">
            <t t-set="dummy" t-value="this.computeActions()"/>
            <div class="o-mail-Message position-relative rounded-0 bg-inherit"
                t-att-data-starred="this.message.starred"
                t-att-data-persistent="this.message.persistent"
                t-att-class="this.attClass"
                role="group"
                t-att-aria-label="this.messageTypeText"
                t-on-click="this.onClick"
                t-on-contextmenu="this.onContextMenu"
                t-on-mouseenter="this.onMouseenter"
                t-on-mouseleave="this.onMouseleave"
                t-ref="root"
                t-if="this.message.exists()"
            >
                <MessageContextMenu anchorRef="this.rightClickAnchor" dropdownState="this.rightClickDropdownState" message="this.message" thread="this.props.thread"/>
                <div class="o-mail-Message-jumpTarget position-absolute top-0 pe-none"/>
                <div t-if="this.props.asCard and this.isMobileOS" class="position-absolute end-0 z-1 m-n2"><t t-call="mail.Message.actions"/></div>
                <div class="o-mail-Message-core position-relative d-flex flex-shrink-0 bg-inherit">
                    <div class="o-mail-Message-sidebar d-flex flex-shrink-0 align-items-center flex-column bg-inherit" t-att-class="{ 'align-items-start': !this.isAlignedRight, 'o-inChatWindow': this.env.inChatWindow }">
                        <t t-if="!this.props.squashed">
                            <div class="o-mail-Message-avatarContainer position-relative bg-inherit rounded-3" t-att-class="this.getAvatarContainerAttClass()">
                                <img class="o-mail-Message-avatar w-100 h-100 rounded-3" t-att-src="this.authorAvatarUrl" t-att-class="this.authorAvatarAttClass"/>
                            </div>
                            <t t-if="this.message.starred" t-call="mail.Message.sidebarStarred"/>
                        </t>
                        <t t-elif="this.message.isPending" t-call="mail.Message.pendingStatus"/>
                        <t t-elif="!this.message.is_transient">
                            <small t-if="this.isActive and this.props.showDates" class="o-mail-Message-date o-xsmaller mt-2 text-center lh-1" t-att-title="this.message.datetimeShort">
                                <t t-esc="this.message.dateSimple"/>
                            </small>
                            <t t-elif="this.message.starred" t-call="mail.Message.sidebarStarred"/>
                        </t>
                    </div>
                    <div class="w-100 o-min-width-0" t-att-class="{ 'flex-grow-1': this.isEditing }" t-ref="messageContent">
                        <div t-if="!this.props.squashed" class="o-mail-Message-header d-flex flex-wrap align-items-baseline lh-1" t-att-class="{ 'mb-1': !this.message.isNote, 'pe-2': this.props.asCard and this.isMobileOS }" name="header">
                            <span t-if="this.message.authorName and this.shouldDisplayAuthorName" class="o-mail-Message-author smaller" t-att-class="this.getAuthorAttClass()">
                                <strong class="me-1 o-fw-600" t-esc="this.message.authorName"/>
                            </span>
                            <t t-if="!this.isAlignedRight" t-call="mail.Message.notification"/>
                            <t t-if="this.isAlignedRight and !this.message.bubbleColor and !(this.props.asCard and this.isMobileOS)" t-call="mail.Message.actions"/>
                            <small t-if="!this.message.is_transient" class="o-mail-Message-date o-xsmaller" t-att-title="this.message.datetimeShort">
                                <t t-if="this.message.isPending" t-call="mail.Message.pendingStatus"/>
                                <t t-else="" t-out="this.message.dateSimpleWithDay"/>
                            </small>
                            <small t-if="this.isPersistentMessageFromAnotherThread" t-on-click.prevent="this.openRecord" class="ms-1 text-500">
                                <t t-if="this.message.channel_id">
                                    (from <a t-att-href="this.message.resUrl"><t t-esc="this.message.thread.prefix"/><t t-esc="this.message.channel_id.displayName or this.message.default_subject"/></a>)
                                </t>
                                <t t-else="">
                                    on <a t-if="this.message.thread.displayName" t-att-href="this.message.resUrl" t-esc="this.message.thread.displayName"/><em class="pe-1 text-decoration-line-through" t-else="">Deleted document</em>
                                </t>
                            </small>
                            <div t-if="this.props.message.scheduledDatetime" t-att-class="{ 'ms-2': (this.env.inChatWindow and this.isAlignedRight) or (this.isPersistentMessageFromAnotherThread) }" t-att-title="this.props.message.scheduledDateSimple">
                                <span class="text-600 cursor-pointer">
                                    <i class="fa fa-calendar-o"/>
                                </span>
                            </div>
                            <t t-if="this.isAlignedRight" t-call="mail.Message.notification"/>
                            <t t-if="!this.isAlignedRight and !this.message.bubbleColor and !(this.props.asCard and this.isMobileOS)" t-call="mail.Message.actions"/>
                        </div>
                        <div class="o-mail-Message-contentContainer position-relative d-flex" t-att-class="{ 'flex-row-reverse': this.isAlignedRight }">
                            <div class="o-mail-Message-content o-min-width-0" t-att-class="{ 'w-100': this.isEditing, 'opacity-50': this.message.isPending, 'pt-1': this.message.isNote, 'o-mail-Message-pollContent flex-grow-1': this.message.poll }">
                                <div class="o-mail-Message-textContent position-relative d-flex" t-att-class="{ 'w-100': this.isEditing }">
                                    <t t-set="showTextVisually" t-value="!this.message.linkPreviewSquash and (this.message.hasTextContent or this.message.subtype_id?.description or this.message.isEmpty)"/>
                                    <t t-if="this.message.message_type === 'notification' and this.message.richBody" t-call="mail.Message.bodyAsNotification" name="bodyAsNotification"/>
                                    <t t-if="this.message.isEmpty or (this.message.message_type !== 'notification' and !this.message.is_transient and (this.message.hasTextContent or this.message.subtype_id?.description or this.isEditing or this.message.parent_id))">
                                        <MessageLinkPreviewList t-if="!this.isEditing and this.message.linkPreviewSquash and !this.message.parent_id" messageLinkPreviews="this.message.message_link_preview_ids"/>
                                        <t t-else="">
                                            <div t-if="this.message.bubbleColor and !this.props.squashed" class="o-mail-Message-bubbleTail position-absolute d-flex" t-att-style="this.isAlignedRight ? 'right: -4px; transform: rotateY(180deg);' : 'left: -4px;'" t-att-class="{
                                                'o-blue': this.message.bubbleColor === 'blue',
                                                'o-green': this.message.bubbleColor === 'green',
                                                'o-orange': this.message.bubbleColor === 'orange',
                                            }">
                                                <svg viewBox="0 0 6 12" height="12" width="6" x="0px" y="0px">
                                                    <path class="o-mail-Message-bubbleTailBorder" fill="currentColor" d="M 0, 0 L 5, 9 V 0 z"/>
                                                    <path class="o-mail-Message-bubbleTailBg" fill="currentColor" d="M 2, 1 L 5, 7 V 1 z"/>
                                                </svg>
                                            </div>
                                            <div class="position-relative overflow-x-auto overflow-y-hidden d-inline-block o-discuss-text-body" t-att-class="{
                                                'w-100': this.isEditing,
                                                'o-rounded-bubble': this.message.bubbleColor and this.props.squashed,
                                                'o-rounded-bottom-bubble': this.message.bubbleColor and !this.props.squashed,
                                                'o-rounded-start-bubble': this.message.bubbleColor and !this.props.squashed and this.isAlignedRight,
                                                'o-rounded-end-bubble': this.message.bubbleColor and !this.props.squashed and !this.isAlignedRight,
                                            }">
                                                <div t-if="this.message.bubbleColor" class="o-mail-Message-bubble position-absolute top-0 start-0 w-100 h-100 border" t-att-class="{
                                                    'o-rounded-bubble': this.props.squashed,
                                                    'o-rounded-bottom-bubble': !this.props.squashed,
                                                    'o-rounded-start-bubble': !this.props.squashed and this.isAlignedRight,
                                                    'o-rounded-end-bubble': !this.props.squashed and !this.isAlignedRight,
                                                    'o-blue': this.message.bubbleColor === 'blue',
                                                    'o-green': this.message.bubbleColor === 'green',
                                                    'o-orange': this.message.bubbleColor === 'orange',
                                                }"/>
                                                <MessageInReply t-if="this.message.parent_id" class="'mx-2 p-1 pb-0 ' + (showTextVisually ? 'mt-1' : 'my-1')" message="this.message" onClick="this.props.onParentMessageClick"/>
                                                <div class="position-relative text-break o-mail-Message-body" t-att-class="{
                                                            'p-1': this.message.isNote,
                                                            'fs-1': !this.isEditing and !this.env.inChatter and this.message.onlyEmojis,
                                                            'mb-0': !this.message.isNote,
                                                            'py-2': !this.message.isNote and !this.isEditing and showTextVisually,
                                                            'pt-2 pb-1': !this.message.isNote and this.isEditing,
                                                            'o-note': this.message.isNote,
                                                            'o-rounded-bubble': this.props.squashed,
                                                            'align-self-start o-rounded-end-bubble o-rounded-bottom-bubble': !this.isEditing and !this.message.isNote and !this.props.squashed,
                                                            'flex-grow-1': this.isEditing,
                                                            }" t-ref="body">
                                                    <i t-if="this.message.isEmpty" class="text-muted opacity-75" t-out="this.message.inlineBody"/>
                                                    <Composer t-elif="this.isEditing" autofocus="true" composer="this.message.composer" onDiscardCallback.bind="this.exitEditMode" onPostCallback.bind="this.exitEditMode" mode="'compact'" sidebar="false"/>
                                                    <t t-else="">
                                                        <em t-if="this.message.subject and !this.message.isSubjectSimilarToThreadName and !this.message.isSubjectDefault" class="d-block text-muted smaller">Subject: <t t-out="this.props.messageSearch?.highlight(this.message.subject) ?? this.message.subject"/></em>
                                                        <div class="overflow-x-auto" t-if="this.message.message_type and this.message.message_type.includes('email')" t-ref="shadowBody"/>
                                                        <t t-elif="this.message.showTranslation" t-out="this.message.richTranslationValue"/>
                                                        <div class="o-mail-Message-richBody overflow-x-auto" t-elif="this.message.hasTextContent and this.message.richBody and !this.message.linkPreviewSquash" t-out="this.props.messageSearch?.highlight(this.message.richBody) ?? this.message.richBody"/>
                                                        <p class="fst-italic text-muted small" t-if="this.message.showTranslation">
                                                            <t t-if="this.message.translationSource" t-esc="this.translatedFromText"/>
                                                        </p>
                                                        <p class="fst-italic text-muted small" t-if="this.message.translationErrors">
                                                            <i class="text-danger fa fa-warning" role="img" aria-label="Translation Failure"/>
                                                            <t t-if="this.message.translationErrors" t-esc="this.translationFailureText"/>
                                                        </p>
                                                        <t t-if="this.showSubtypeDescription" t-out="this.props.messageSearch?.highlight(this.message.subtype_id?.description) ?? this.message.subtype_id?.description"/>
                                                    </t>
                                                </div>
                                            </div>
                                        </t>
                                    </t>
                                    <t t-if="this.message.bubbleColor and this.message.hasTextContent and !this.env.inChatWindow and !(this.props.asCard and this.isMobileOS)" t-call="mail.Message.actions"/>
                                    <PollResult t-if="this.message.ended_poll_ids.length" poll="this.message.poll"/>
                                    <Poll t-elif="this.message.poll" poll="this.message.poll"/>
                                </div>
                                <div class="position-relative">
                                    <AttachmentList
                                        t-if="this.message.attachment_ids.length > 0"
                                        attachments="this.message.attachment_ids.map((a) => a)"
                                        unlinkAttachment.bind="this.onClickAttachmentUnlink"
                                        messageSearch="this.props.messageSearch"/>
                                </div>
                                <MessageLinkPreviewList t-if="(this.message.message_link_preview_ids.length > 0 and this.store.hasLinkPreviewFeature and !this.message.linkPreviewSquash) or (!this.isEditing and this.message.linkPreviewSquash and this.message.parent_id)" messageLinkPreviews="this.message.message_link_preview_ids"/>
                            </div>
                            <t t-if="this.message.bubbleColor and (!this.message.hasTextContent or this.env.inChatWindow) and !(this.props.asCard and this.isMobileOS)" t-call="mail.Message.actions"/>
                        </div>
                        <MessageReactions message="this.message" openReactionMenu="this.openReactionMenu" t-if="this.message.reactions.length"/>
                        <t name="after-reactions"/>
                    </div>
                </div>
            </div>
        </ActionSwiper>
    </t>
    """,
    },
]

tcall_param_tests = [
    {
        "name": "tcall-param basic",
        "content": """<t t-call="my.Template">
    <t t-set="foo" t-value="bar"/>
</t>""",
        "expected": """<t t-call="my.Template" foo="bar"/>""",
    },
    {
        "name": "tcall-param translate",
        "content": """<t t-call="my.Template">
    <t t-set="title">Hello World</t>
</t>""",
        "expected": """<t t-call="my.Template" title.translate="Hello World"/>""",
    },
    {
        "name": "tcall-param used-inside",
        "content": """<div>
    <t t-call="my.Template">
        <t t-set="foo" t-value="bar"/>
        <t t-out="foo"/>
    </t>
</div>""",
        # foo is used inside call body → stays in place; no transformation applied
        "expected": """<div>
    <t t-call="my.Template">
        <t t-set="foo" t-value="bar"/>
        <t t-out="foo"/>
    </t>
</div>""",
    },
    {
        "name": "tcall-param only t-directives",
        # t-call with non-t- attributes is skipped; inner t-set stays
        "content": """<div>
    <t t-call="my.Template">
        <t t-set="x" t-value="v"/>
    </t>
    <t t-call="other.Template" class="extra">
        <t t-set="y" t-value="w"/>
    </t>
</div>""",
        "expected": """<div>
    <t t-call="my.Template" x="v"/>
    <t t-call="other.Template" class="extra">
        <t t-set="y" t-value="w"/>
    </t>
</div>""",
    },
    {
        "name": "tcall-param auto-close",
        "content": """<t t-call="my.Template">
    <t t-set="foo" t-value="bar">
    </t>
</t>""",
        "expected": """<t t-call="my.Template" foo="bar"/>""",
    },
]

# ------------------------------------------------------------------------------


def run_test_specific_modules(test):
    variables = test.get("inside_vars", {})
    modules = test.get("modules", False)
    path = test.get("path", False)

    aggregator = VariableAggregator(is_testing=True)
    aggregator.all_vars = variables

    res, _ = update_template(path, test["content"], modules, aggregator, {})
    return res


test_external_xpath = [
    {
        "name": "No replace on inherits targetting modules not in target modules",
        "inside_vars": defaultdict(set),
        "path": "",
        "modules": ["website"],
        "content": """
<templates id="template" xml:space="preserve">
    <t t-name="account_accountant.AttachmentPreviewListView" t-inherit="web.ListView">
        <xpath expr="//t[@t-component='props.Renderer']" position="attributes">
            <attribute name="setSelectedRecord.bind">this.setSelectedRecord</attribute>
        </xpath>
    </t>
</templates>""",
        "expected": """
<templates id="template" xml:space="preserve">
    <t t-name="account_accountant.AttachmentPreviewListView" t-inherit="web.ListView">
        <xpath expr="//t[@t-component='props.Renderer']" position="attributes">
            <attribute name="setSelectedRecord.bind">this.setSelectedRecord</attribute>
        </xpath>
    </t>
</templates>""",
    },
    {
        "name": "Only replace in files not in path",
        "inside_vars": defaultdict(set),
        "path": "",
        "modules": ["web"],
        "content": """ <templates id="template" xml:space="preserve"> <t t-if="showDelete"> a </t> </templates>""",
        "expected": """ <templates id="template" xml:space="preserve"> <t t-if="showDelete"> a </t> </templates>""",
    },
    {
        "name": "Replace x-path if they target correct module",
        "inside_vars": defaultdict(set),
        "path": "",
        "modules": ["web"],
        "content": """
<templates id="template" xml:space="preserve">
    <t t-name="account_accountant.AttachmentPreviewListView" t-inherit="web_bridge.ListView">
        <xpath expr="//t[@t-component='props.Renderer']" position="replace">
            <button t-if="showDelete"/>
        </xpath>
    </t>
</templates>""",
        "expected": """
<templates id="template" xml:space="preserve">
    <t t-name="account_accountant.AttachmentPreviewListView" t-inherit="web_bridge.ListView">
        <xpath expr="//t[@t-component='this.props.Renderer']" position="replace">
            <button t-if="this.showDelete"/>
        </xpath>
    </t>
</templates>""",
    },
    {
        "name": "Replace inside x-path with variables",
        "inside_vars": {"web.ListView": {"showDelete"}},
        "path": "",
        "modules": ["web"],
        "content": """
<templates id="template" xml:space="preserve">
    <t t-name="account_accountant.AttachmentPreviewListView" t-inherit="web.ListView">
        <xpath expr="//t[@t-component='showDelete']" position="replace">
            <t t-if="showDelete"> a </t>
            <t t-elif="other"> b </t>
        </xpath>
    </t>
</templates>""",
        "expected": """
<templates id="template" xml:space="preserve">
    <t t-name="account_accountant.AttachmentPreviewListView" t-inherit="web.ListView">
        <xpath expr="//t[@t-component='showDelete']" position="replace">
            <t t-if="showDelete"> a </t>
            <t t-elif="this.other"> b </t>
        </xpath>
    </t>
</templates>""",
    },
    {
        "name": "xpath targetting non t attributes",
        "content": """
<t t-name="esg_csrd.OptionsDropdown" t-inherit="knowledge.OptionsDropdown" t-inherit-mode="extension">
    <xpath expr="//DropdownItem[@onSelected.bind='exportAuditReportToPDF']" position="after"><A/></xpath>
    <xpath expr="//DropdownItem[@onSelected='exportAuditReportToPDF']" position="after"><A/></xpath>
    <xpath expr="//DropdownItem[@onChange.alike='isChecked']" position="after"><A/></xpath>
    <xpath expr="//CheckBox[@value='includeArchived']" position="replace"><A/></xpath>
    <xpath expr="//option[@value='includeArchived']" position="replace"><A/></xpath>
    <xpath expr="//label[@for='includeArchived']" position="replace"><A/></xpath>
</t>
""",
        "expected": """
<t t-name="esg_csrd.OptionsDropdown" t-inherit="knowledge.OptionsDropdown" t-inherit-mode="extension">
    <xpath expr="//DropdownItem[@onSelected.bind='this.exportAuditReportToPDF']" position="after"><A/></xpath>
    <xpath expr="//DropdownItem[@onSelected='this.exportAuditReportToPDF']" position="after"><A/></xpath>
    <xpath expr="//DropdownItem[@onChange.alike='this.isChecked']" position="after"><A/></xpath>
    <xpath expr="//CheckBox[@value='this.includeArchived']" position="replace"><A/></xpath>
    <xpath expr="//option[@value='includeArchived']" position="replace"><A/></xpath>
    <xpath expr="//label[@for='includeArchived']" position="replace"><A/></xpath>
</t>
""",
    },
    {
        "name": "Replace x-path if they target bridge module",
        "inside_vars": defaultdict(set),
        "path": "",
        "modules": ["web"],
        "content": """
<templates id="template" xml:space="preserve">
    <t t-name="account_accountant.AttachmentPreviewListView" t-inherit="web_tour.ListView">
        <xpath expr="//div[@t-ref='root']" position="attributes" type="add">
            <attribute name="class" add="o_move_line_list_view" separator=" "/>
        </xpath>
        <xpath expr="//t[@t-component='props.Renderer']" position="attributes">
            <attribute name="setSelectedRecord.bind">this.setSelectedRecord</attribute>
        </xpath>
        <xpath expr="//Layout" position="inside">
            <t t-call="account_accountant.AttachmentPreview"/>
        </xpath>
    </t>
    <t t-name="account_accountant.BankRecoKanbanController" t-inherit="crm.KanbanView" t-inherit-mode="primary">
        <xpath expr="//t[@t-component='props.Renderer']" position="attributes">
            <attribute name="className">'o_bank_reconciliation_container d-flex'</attribute>
        </xpath>
    </t>
</templates>
        """,
        "expected": """
<templates id="template" xml:space="preserve">
    <t t-name="account_accountant.AttachmentPreviewListView" t-inherit="web_tour.ListView">
        <xpath expr="//div[@t-ref='root']" position="attributes" type="add">
            <attribute name="class" add="o_move_line_list_view" separator=" "/>
        </xpath>
        <xpath expr="//t[@t-component='this.props.Renderer']" position="attributes">
            <attribute name="setSelectedRecord.bind">this.setSelectedRecord</attribute>
        </xpath>
        <xpath expr="//Layout" position="inside">
            <t t-call="account_accountant.AttachmentPreview"/>
        </xpath>
    </t>
    <t t-name="account_accountant.BankRecoKanbanController" t-inherit="crm.KanbanView" t-inherit-mode="primary">
        <xpath expr="//t[@t-component='props.Renderer']" position="attributes">
            <attribute name="className">'o_bank_reconciliation_container d-flex'</attribute>
        </xpath>
    </t>
</templates>
        """,
    },
]

# ------------------------------------------------------------------------------


def run_test_exclude_modules(test):
    modules = test.get("modules", False)
    path = test.get("path", False)

    aggregator = VariableAggregator(is_testing=True)
    aggregator.inherit_map = {'web.abc': 'web.xyz'}

    res, _ = update_template(path, test["content"], modules, aggregator, test.get('excluded_templates', {}))
    return res


test_exclude_templates = [
    {
        "name": "no exclude",
        "excluded_templates": {},
        "content": """<t t-name="web.xyz"> <t t-out="value"/> </t>""",
        "expected": """<t t-name="web.xyz"> <t t-out="this.value"/> </t>""",
    },
    {
        "name": "exclude only one template",
        "excluded_templates": {'web.xyz'},
        "content": """
            <templates id="template" xml:space="preserve">
                <t t-name="web.xyz"> <t t-out="value"/> </t>
                <t t-name="web.abc"> <t t-out="value"/> </t>
            </templates>
        """,
        "expected": """
            <templates id="template" xml:space="preserve">
                <t t-name="web.xyz"> <t t-out="value"/> </t>
                <t t-name="web.abc"> <t t-out="this.value"/> </t>
            </templates>
        """,
    },
    {
        "name": "exclude nested templates",
        "excluded_templates": {'web.xyz'},
        "content": """
            <templates id="template" xml:space="preserve">
                <t t-name="web.xyz"> <t t-out="foo"/> </t>
                <t t-name="web.abc" t-inherit="web.xyz" t-inherit-mode="primary">
                    <xpath expr="//t[@t-if='bar']" position="after">
                        <t t-out="baz"/>
                    </xpath>
                </t>
            </templates>
        """,
        "expected": """
            <templates id="template" xml:space="preserve">
                <t t-name="web.xyz"> <t t-out="foo"/> </t>
                <t t-name="web.abc" t-inherit="web.xyz" t-inherit-mode="primary">
                    <xpath expr="//t[@t-if='bar']" position="after">
                        <t t-out="baz"/>
                    </xpath>
                </t>
            </templates>
        """,
    },
]

# ------------------------------------------------------------------------------


def run_test_vars(test):
    aggregator = VariableAggregator(is_testing=True)
    if "all_vars" in test or "outside_vars" in test:
        aggregator.all_vars = test.get("all_vars", {})
        aggregator.t_call_vars = test.get("outside_vars", defaultdict(set))
        aggregator.full_inherit_and_call_map = test.get("full_inherit_and_call_map", defaultdict(str))
    else:
        # If vars not specified replicate the real process of using aggregator to map
        def agg_callback(tree):
            aggregator.aggregate_inside_vars(tree)
            aggregator.aggregate_call_vars(tree)
            aggregator.link_templates(tree)
        update_etree(test["content"], agg_callback)
        aggregator.map_inherits_and_calls()

    res, _ = update_template("", test["content"], False, aggregator, {})
    return res


test_vars = [
    {
        "name": "vars basic",
        "outside_vars": {"abc": {"a"}},
        "all_vars": {},
        "content": '<t t-name="abc"><t t-out="a"/><t t-out="b"/></t>',
        "expected": '<t t-name="abc"><t t-out="a"/><t t-out="this.b"/></t>',
    },
    {
        "name": "x path with no local vars",
        "all_vars": defaultdict(set),
        "outside_vars": defaultdict(set),
        "content": """
<templates id="template" xml:space="preserve">
    <t t-name="account_accountant.AttachmentPreviewListView" t-inherit="web.ListView">
        <xpath expr="//t[@t-component='props.Renderer']" position="attributes">
            <attribute name="setSelectedRecord.bind">setSelectedRecord</attribute>
        </xpath>
    </t>
</templates>
        """,
        "expected": """
<templates id="template" xml:space="preserve">
    <t t-name="account_accountant.AttachmentPreviewListView" t-inherit="web.ListView">
        <xpath expr="//t[@t-component='this.props.Renderer']" position="attributes">
            <attribute name="setSelectedRecord.bind">this.setSelectedRecord</attribute>
        </xpath>
    </t>
</templates>
        """,
    },
    {
        "name": "x path with local vars",
        "all_vars": {"web.ListView": {"item"}},
        "outside_vars": defaultdict(set),
        "content": """
<templates id="template" xml:space="preserve">
    <t t-name="account_accountant.AttachmentPreviewListView" t-inherit="web.ListView">
        <xpath expr="//Navbar" position="attributes">
            <attribute name="setSelectedRecord.bind">item</attribute>
            <attribute name="aaaa">notitem</attribute>
        </xpath>
    </t>
</templates>
        """,
        "expected": """
<templates id="template" xml:space="preserve">
    <t t-name="account_accountant.AttachmentPreviewListView" t-inherit="web.ListView">
        <xpath expr="//Navbar" position="attributes">
            <attribute name="setSelectedRecord.bind">item</attribute>
            <attribute name="aaaa">this.notitem</attribute>
        </xpath>
    </t>
</templates>
        """,
    },
    {
        "name": "x path with outside vars",
        "all_vars": defaultdict(set),
        "outside_vars": {"web.ListView": {"item"}},
        "content": """
<templates id="template" xml:space="preserve">
    <t t-name="account_accountant.AttachmentPreviewListView" t-inherit="web.ListView">
        <xpath expr="//Navbar" position="attributes">
            <attribute name="setSelectedRecord.bind">item</attribute>
            <attribute name="aaaa">notitem</attribute>
        </xpath>
    </t>
</templates>
        """,
        "expected": """
<templates id="template" xml:space="preserve">
    <t t-name="account_accountant.AttachmentPreviewListView" t-inherit="web.ListView">
        <xpath expr="//Navbar" position="attributes">
            <attribute name="setSelectedRecord.bind">item</attribute>
            <attribute name="aaaa">this.notitem</attribute>
        </xpath>
    </t>
</templates>
        """,
    },
    {
        "name": "t-att-for with global vars",
        "all_vars": {'web.RadioField': {'item'}},
        "outside_vars": defaultdict(set),
        "content": """
<t t-name="web.SettingsRadioField" t-inherit="web.RadioField" t-inherit-mode="primary">
    <xpath expr="//label" position="replace">
        <label class="form-check-label o_form_label" t-att-for="`${id}_${item[0]}`">
            <HighlightText originalText="item[1]"/>
        </label>
    </xpath>
</t>
        """,
        "expected": """
<t t-name="web.SettingsRadioField" t-inherit="web.RadioField" t-inherit-mode="primary">
    <xpath expr="//label" position="replace">
        <label class="form-check-label o_form_label" t-att-for="`${this.id}_${item[0]}`">
            <HighlightText originalText="item[1]"/>
        </label>
    </xpath>
</t>
        """,
    },
    {
        "name": "t-call outer vars (t-set before t-call)",
        "all_vars": defaultdict(set),
        "outside_vars": defaultdict(set),
        "t_call_outer_vars": {"web.Department": {"dept", "hideTree"}},
        "content": '<t t-name="web.Department"><t t-out="dept"/><t t-out="other"/></t>',
        "expected": '<t t-name="web.Department"><t t-out="dept"/><t t-out="this.other"/></t>',
    },
    {
        "name": "t-custom-ref xpath",
        "all_vars": defaultdict(set),
        "outside_vars": defaultdict(set),
        "content": """
<t t-name="web.SettingsRadioField" t-inherit="web.RadioField" t-inherit-mode="primary">
    <xpath expr="//div[@t-custom-ref='root']" position="attributes">
        <attribute name="t-on-dragenter.prevent">kanbanDragEnter</attribute>
    </xpath>
</t>
        """,
        "expected": """
<t t-name="web.SettingsRadioField" t-inherit="web.RadioField" t-inherit-mode="primary">
    <xpath expr="//div[@t-custom-ref='root']" position="attributes">
        <attribute name="t-on-dragenter.prevent">this.kanbanDragEnter</attribute>
    </xpath>
</t>
        """,
    },
    {
        "name": "t t-name with position",
        "all_vars": {"sale_management.ListRenderer.RecordRow": {'record'}},
        "outside_vars": defaultdict(set),
        "content": """
            <templates>
                <t
                    t-name="sale_management.ListRenderer.RecordRow"
                    t-inherit="account.SectionAndNoteListRenderer.RecordRow"
                    t-inherit-mode="primary"
                >
                    <t t-name="composition_button" position="after">
                        <DropdownItem
                            onSelected="() => this.toggleIsOptional(this.record)"
                            attrs="{ 'class': this.disableOptionalButton(this.record) ? 'disabled' : '' }"
                        >
                            <i class="me-1 fa fa-fw fa-dot-circle-o"/>
                            <span t-if="record.data.is_optional">Unset Optional</span>
                            <span t-else="">Set Optional</span>
                        </DropdownItem>
                    </t>
                </t>
            </templates>
        """,
        "expected": """
            <templates>
                <t
                    t-name="sale_management.ListRenderer.RecordRow"
                    t-inherit="account.SectionAndNoteListRenderer.RecordRow"
                    t-inherit-mode="primary"
                >
                    <t t-name="composition_button" position="after">
                        <DropdownItem
                            onSelected="() => this.toggleIsOptional(this.record)"
                            attrs="{ 'class': this.disableOptionalButton(this.record) ? 'disabled' : '' }"
                        >
                            <i class="me-1 fa fa-fw fa-dot-circle-o"/>
                            <span t-if="record.data.is_optional">Unset Optional</span>
                            <span t-else="">Set Optional</span>
                        </DropdownItem>
                    </t>
                </t>
            </templates>
        """,
    },
    {
        "name": "t-set before t-call inside component",
        "content": """
<templates>
    <t t-name="web.Caller">
        <Dialog>
            <t t-set="passedVar" t-value="compVar"/>
            <t t-call="web.Callee"/>
        </Dialog>
    </t>
    <t t-name="web.Callee">
        <div t-att-class="passedVar"/>
    </t>
</templates>
""",
        "expected": """
<templates>
    <t t-name="web.Caller">
        <Dialog>
            <t t-set="passedVar" t-value="this.compVar"/>
            <t t-call="web.Callee"/>
        </Dialog>
    </t>
    <t t-name="web.Callee">
        <div t-att-class="passedVar"/>
    </t>
</templates>
""",
    },
    {
        "name": "inherited vars from parent not prefixed with this.",
        "content": """
<templates>
    <t t-name="web.Parent">
        <t t-set="parentVar" t-value="someValue"/>
        <t t-out="parentVar"/>
    </t>
    <t t-name="web.Child" t-inherit="web.Parent" t-inherit-mode="primary">
        <xpath expr="//t[@t-set='parentVar']" position="after">
            <t t-out="parentVar"/>
            <t t-out="otherVar"/>
        </xpath>
    </t>
</templates>
""",
        "expected": """
<templates>
    <t t-name="web.Parent">
        <t t-set="parentVar" t-value="this.someValue"/>
        <t t-out="parentVar"/>
    </t>
    <t t-name="web.Child" t-inherit="web.Parent" t-inherit-mode="primary">
        <xpath expr="//t[@t-set='parentVar']" position="after">
            <t t-out="parentVar"/>
            <t t-out="this.otherVar"/>
        </xpath>
    </t>
</templates>
""",
    },
]


# ------------------------------------------------------------------------------


def run_test_aggregator(test):
    aggregator = VariableAggregator(is_testing=True)

    if "inside_vars" in test:
        aggregator.all_vars.update(test["inside_vars"])
    if "outside_vars" in test:
        aggregator.t_call_vars.update(test["outside_vars"])

    # Run variable aggregation
    def callback(tree):
        aggregator.aggregate_inside_vars(tree)
        aggregator.aggregate_call_vars(tree)
        aggregator.link_templates(tree)
    update_etree(test["content"], callback)

    # Convert defaultdicts to standard dicts for clean printing/comparison
    result = {}
    if aggregator.all_vars:
        result["all_vars"] = dict(aggregator.all_vars)
    if aggregator.t_call_vars:
        result["t_call_inner"] = dict(aggregator.t_call_vars)
    if aggregator.t_call_outer_vars:
        result["t_call_outer"] = dict(aggregator.t_call_outer_vars)

    if aggregator.all_templates:
        inherit_map = dict()
        full_inherit_and_call_map = dict()
        for template_name in aggregator.all_templates:
            template = aggregator.all_templates[template_name]

            full_inherit_and_call_map[template_name] = list(template.get_dependencies())

            # Inherit map
            if template.parent is not None:
                inherit_map[template_name] = template.parent.name
        if inherit_map:
            result["inherit_map"] = inherit_map
        if full_inherit_and_call_map:
            result["full_inherit_and_call_map"] = full_inherit_and_call_map

    return result


test_vars_collection = [
    {
        "name": "simple template",
        "inside_vars": {"abc": {"a"}},
        "content": '<t t-name="web.xyz"> <t t-set="b" t-value="2"/> </t>',
        "expected": {"all_vars": {'abc': {'a'}, 'web.xyz': {'b'}}, 'full_inherit_and_call_map': {'web.xyz': []}},
    },
    {
        "name": "t-slot-scope-vars",
        "content": """
<t t-name="web.Many2XAutocomplete" >
    <div class="o_input_dropdown" t-ref="autocomplete_container">
        <AutoComplete t-else="" t-props="autoCompleteProps">
            <t t-set-slot="option" t-slot-scope="optionScope">
                <t t-slot="{{ optionScope.data.slotName }}" t-props="optionScope.data" label="optionScope.label">
                    <t t-out="optionScope.label"/>
                </t>
            </t>
        </AutoComplete>
        <span class="o_dropdown_button" />
    </div>
</t>
        """,
        "expected": {"all_vars": {'web.Many2XAutocomplete': {'optionScope'}}, 'full_inherit_and_call_map': {'web.Many2XAutocomplete': []}},
    },
    {
        "name": "t-call",
        "content": """
<t t-name="web.xyz" >
    <t t-set="outside" t-value="2"/>
    <t t-call="mail.zzz"> <t t-set="inside" t-value="a"/> </t>
</t>
        """,
        "expected": {
            "all_vars": {'web.xyz': {'outside'}},
            "t_call_inner": {'mail.zzz': {'inside'}},
            "t_call_outer": {'mail.zzz': {'outside'}},
            'full_inherit_and_call_map': {'web.xyz': [], 'mail.zzz': ['web.xyz']}
        },
    },
    {
        "name": "t-call with inline params",
        "content": """
<t t-name="web.xyz" >
    <t t-call="web.SectionMenu" section="subSection" isNested="true"/>
</t>
        """,
        "expected": {
            "all_vars": {'web.xyz': set()},
            "t_call_inner": {'web.SectionMenu': {'section', 'isNested'}},
            "t_call_outer": {'web.SectionMenu': set()},
            'full_inherit_and_call_map': {'web.xyz': [], 'web.SectionMenu': ['web.xyz']}
        },
    },
    {
        "name": "t-slot-scope",
        "content": """
<t t-name="web.xyz">
    <Record t-slot-scope="data"/>
</t>
        """,
        "expected": {
            "all_vars": {'web.xyz': {'data'}},
            'full_inherit_and_call_map': {'web.xyz': []}
        },
    },
    {
        "name": "Nested Inherits",
        "excluded_templates": {'web.xyz'},
        "content": """
            <templates id="template" xml:space="preserve">
                <t t-name="web.xyz"> <t t-out="foo"/> </t>
                <t t-name="web.abc" t-inherit="web.xyz" t-inherit-mode="primary">
                    <xpath expr="//t[@t-if='bar']" position="after">
                        <t t-out="baz"/>
                    </xpath>
                </t>
            </templates>
        """,
        "expected": {'all_vars': {'web.xyz': set(), 'web.abc': set()}, 'inherit_map': {'web.abc': 'web.xyz'}, 'full_inherit_and_call_map':  {'web.xyz': [], 'web.abc': ['web.xyz']}},
    },
    {
        "name": "Nested Inherits t-call",
        "excluded_templates": {'web.xyz'},
        "content": """
            <templates id="template" xml:space="preserve">
                <t t-name="web.a"> t-set var </t>
                <t t-name="web.b" t-inherit="web.a" t-inherit-mode="primary">
                     <t t-call="web.c"> </t>
                </t>
                <t t-name="web.c">
                    <t t-call="web.d"> </t>
                </t>
                <t t-name="web.e" t-inherit="web.c" t-inherit-mode="primary"></t>
            </templates>
        """,
        "expected": {
            'all_vars': {'web.a': set(), 'web.b': set(), 'web.c': set(), 'web.e': set()},
            't_call_outer': {'web.c': set(), 'web.d': set()},
            'inherit_map': {'web.b': 'web.a', 'web.e': 'web.c'},
            'full_inherit_and_call_map': {'web.a': [], 'web.b': ['web.a'], 'web.c': ['web.b', 'web.a'], 'web.d': ['web.c', 'web.b', 'web.a'], 'web.e': ['web.c', 'web.b', 'web.a']},
        }
    },
]


# ------------------------------------------------------------------------------

def run_test_warnings(test):
    aggregator = VariableAggregator(is_testing=True)
    aggregator.all_vars = test.get("all_vars", {})
    aggregator.inherit_map = test.get("inherit_map", {})
    aggregator.full_inherit_and_call_map = test.get("full_inherit_and_call_map", {})
    aggregator.t_call_outer_vars = test.get("t_call_outer_vars", {})
    _, warnings = update_template("", test["content"], False, aggregator, {})

    return warnings


test_warning_vars = [
    {
        "name": "No warning simple",
        "all_vars": {'web.a': {"b"}},
        "full_inherit_and_call_map": {},
        "content": '<t t-name="web.xyz"> <t t-out="b"/> </t>',
        "expected": [],
    },
    {
        "name": "No warning on direct parent",
        "all_vars": {'web.a': {"b"}},
        "inherit_map": {"web.xyz": "web.a"},
        "full_inherit_and_call_map": {'web.xyz': {'web.a', 'web.b', 'web.c'}},
        "content": '<t t-name="web.xyz" t-inherit="web.a" t-inherit-mode="primary"> <t t-out="b"/> </t>',
        "expected": [],
    },
    #  Deprecated because we now automatically use full inherit chain to set `this`
    # {
    #     "name": "Far away parent warning",
    #     "all_vars": {'web.a': {"b"}},
    #     "full_inherit_and_call_map": {'web.xyz': {'web.a', 'web.b', 'web.c'}},
    #     "content": '<t t-name="web.xyz"> <t t-out="b"/> </t>',
    #     "expected": ["WARNING in template 'web.xyz' : variable 'b' also defined in a far parent."]
    # },
    #  Deprecated because we now automatically discard outer t-call varsY
    # {
    #     "name": "Outer t-call warning",
    #     "t_call_outer_vars": {'web.xyz': {"b"}},
    #     "full_inherit_and_call_map": {'web.xyz': {'web.a', 'web.b', 'web.c'}},
    #     "content": '<t t-name="web.xyz"> <t t-out="b"/> </t>',
    #     "expected": ["WARNING in template 'web.xyz' : t-call-outer variable 'b'."]
    # },
]

# ------------------------------------------------------------------------------


WHITELIST = []


def run_test_group(name, tests, func):
    success = 0
    fail = 0
    print(f"running suite '{name}' ({len(tests)} tests)")  # noqa: T201

    for test in tests:
        name = test.get("name")

        if WHITELIST and name not in WHITELIST:
            continue

        try:
            output = func(test)

            if output != test["expected"]:
                fail += 1
                print(f"{name}: fail")  # noqa: T201
                print("Expected:")  # noqa: T201
                print(test["expected"])  # noqa: T201
                print("Output:")  # noqa: T201
                print(output)  # noqa: T201
            else:
                success += 1
        except Exception as e:  # noqa: BLE001
            fail += 1
            print(f"{name}: fail")  # noqa: T201
            print(e)  # noqa: T201

    return success, fail


if __name__ == "__main__":
    total_success = 0
    total_fail = 0

    for name, test_group, func in [
        ("main", tests, run_tests_main),
        ("tcall_param", tcall_param_tests, run_tests_tcall_param),
        ("xpaths", test_external_xpath, run_test_specific_modules),
        ("excluded templates", test_exclude_templates, run_test_exclude_modules),
        ("external vars", test_vars, run_test_vars),
        ("vars aggregator", test_vars_collection, run_test_aggregator),
        ("warning vars", test_warning_vars, run_test_warnings),
    ]:
        s, f = run_test_group(name, test_group, func)
        total_success += s
        total_fail += f

    if not total_fail:
        print(f"Yep, {total_success} tests passed")  # noqa: T201
