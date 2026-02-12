from tools_etree import get_indentation, update_etree
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
            s = s[m.end() :]
            continue

        for t in TOKENIZERS:
            token = t(s)
            if token:
                tokens.append(token)
                s = s[token.size :]
                break
        else:
            raise ValueError(f"Tokenizer error near: {s}")
    return tokens


# ------------------------------------------------------------------------------
# Compiler
# ------------------------------------------------------------------------------
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


TEMPLATE_EXPR = re.compile(r"\$\{([^}]+)\}")


def compile_expr(expr, bound_variables):
    bound_variables = set(bound_variables)

    leading_ws = len(expr) - len(expr.lstrip(" "))
    trailing_ws = len(expr) - len(expr.rstrip(" "))
    stripped = expr.strip()
    if not stripped:
        return expr

    # stripped = re.sub(r'\u2007', '', stripped)
    tokens = tokenize(stripped)
    local_vars = set()
    stack = []  # track {, [, ( for group context

    # print([(t.value, t.type, len(t.value)) for t in tokens])
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.type == "WHITESPACE":
            i += 1
            continue
        if tok.type == "TEMPLATE_STRING":

            def replace(match):
                inner_expr = match.group(1)
                rewritten = compile_expr(inner_expr, bound_variables)
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
        if next_tok and next_tok.type == "OPERATOR" and next_tok.value == "=\u2007>":
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
            and tok.value not in bound_variables
            and tok.value not in local_vars
            and tok.value != "this"
            and not (prev_tok and prev_tok.type == "OPERATOR" and prev_tok.value == ".")
            and not (
                prev_tok
                and (prev_tok.type == "LEFT_BRACE" or prev_tok.type == "COMMA")
                and next_tok
                and next_tok.type == "COLON"
            )
        ):
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
    return " " * leading_ws + compiled + " " * trailing_ws


INTERP_RE = re.compile(r"(#\{(.*?)\}|\{\{(.*?)\}\})")


def _process_dynamic_string(str, bound_variables):
    def repl(match):
        # Pick the captured group depending on which syntax matched
        expr = match.group(2) if match.group(2) is not None else match.group(3)

        # Preserve leading/trailing spaces inside the interpolation
        leading_ws = len(expr) - len(expr.lstrip(" "))
        trailing_ws = len(expr) - len(expr.rstrip(" "))
        stripped_expr = expr.strip()
        if not stripped_expr:
            return match.group(0)  # empty expression → leave unchanged

        compiled = compile_expr(stripped_expr, bound_variables)
        # Reconstruct using the original delimiters
        if match.group(2) is not None:
            return f"#{{{' ' * leading_ws}{compiled}{' ' * trailing_ws}}}"
        else:
            return f"{{{{{' ' * leading_ws}{compiled}{' ' * trailing_ws}}}}}"

    return INTERP_RE.sub(repl, str)


def process_dynamic_string(node, bound_variables, attr="t-attf-class"):
    value = node.get(attr)
    if not value:
        return

    new_value = _process_dynamic_string(value, bound_variables)
    node.set(attr, new_value)


def is_component(node):
    # print(node)
    return (node.tag and node.tag[0].isupper()) or node.get("t-component") is not None


def process_component_attributes(root, bound_variables):
    for node in iter_elements(root):
        if not isinstance(node.tag, str):
            continue  # skip comments, processing instructions, etc.

        if not is_component(node):
            continue

        for attr, value in node.attrib.items():
            if not value:
                continue
            if attr.startswith("t-") or attr.endswith(".translate"):
                continue  # skip Owl directives
            node.set(attr, compile_expr(value, bound_variables))


def process_t_att_attributes(root, bound_variables):
    for node in iter_elements(root):
        for attr, value in node.attrib.items():
            if attr.startswith("t-att-") and not attr.startswith("t-attf-"):
                node.set(attr, compile_expr(value, bound_variables))


def expand_t_as(name):
    return {
        name,
        f"{name}_index",
        f"{name}_first",
        f"{name}_last",
        f"{name}_value",
    }


def collect_bound_variables(root):
    bound = set()

    for el in iter_elements(root):
        # t-set defines exactly one variable
        t_set = el.get("t-set")
        if t_set:
            bound.add(t_set)

        # t-slot-scope defines exactly one variable
        t_scope = el.get("t-slot-scope")
        if t_scope:
            bound.add(t_scope)

        # t-as defines a family
        t_as = el.get("t-as")
        if t_as:
            bound |= expand_t_as(t_as)

    return bound


T_ATTR_RE = re.compile(r"@t-([\w-]+)='(.*?)'")
COMP_REGEXP = re.compile(r"^//[A-Z]\w*")
SKIP_XPATH_ATTRS = {"name", "ref", "set-slot", "slot"}  # attributes to skip


def process_xpath_expr(expr, bound_variables, skip_attr=SKIP_XPATH_ATTRS):
    def repl(match):
        attr_name = match.group(1)
        js_expr = match.group(2)
        if attr_name in skip_attr:
            # return original string unchanged
            return match.group(0)

        if attr_name == "call":
            new_expr = _process_dynamic_string(js_expr, bound_variables)
        else:
            new_expr = compile_expr(js_expr, bound_variables)
        # preserve quotes
        return match.group(0).replace(js_expr, new_expr)

    return T_ATTR_RE.sub(repl, expr)


def iter_elements(root):
    """Yield only real element nodes (skip comments, PIs, etc.)"""
    for node in root.iter():
        # node.tag is a string for real elements
        if isinstance(node.tag, str):
            yield node


DIRECTIVES = [
    "t-esc",
    "t-out",
    "t-value",
    "t-key",
    "t-if",
    "t-elif",
    "t-foreach",
    "t-component",
    "t-props",
    "t-model",
    "t-tag",
    "t-call-context",
]


def fix_template(root: etree._ElementTree, bound_variables, inside_vars):
    for attr in DIRECTIVES:
        for node in root.xpath(f"descendant-or-self::*[@{attr}]"):
            node.set(attr, compile_expr(node.get(attr), bound_variables))

    for node in iter_elements(root):
        for attr, value in node.attrib.items():
            if attr.startswith("t-on-") and value:
                node.set(attr, compile_expr(value, bound_variables))

    for node in iter_elements(root):
        for attr in node.attrib:
            if attr.startswith("t-attf-"):
                process_dynamic_string(node, bound_variables, attr)
            if attr == "t-call":
                process_dynamic_string(node, bound_variables, attr)
            if attr == "t-ref":
                process_dynamic_string(node, bound_variables, attr)
            if attr == "t-slot":
                process_dynamic_string(node, bound_variables, attr)

    process_t_att_attributes(root, bound_variables)

    process_component_attributes(root, bound_variables)

    for inherit_node in root.xpath("descendant-or-self::*[@t-inherit]"):
        target = inherit_node.get("t-inherit")
        inherit_vars = inside_vars.get(target, {})
        # return
        for node in inherit_node.xpath("descendant-or-self::xpath[@expr]"):
            expr = node.get("expr")
            if expr:
                node.set("expr", process_xpath_expr(expr, inherit_vars))

            for n in root.xpath("descendant-or-self::attribute[@name]"):
                attr = n.get("name")
                if (
                    attr in DIRECTIVES
                    or attr.startswith("t-on-")
                    or attr.startswith("t-att-")
                    or "t-component" in expr
                    or COMP_REGEXP.match(expr)
                ):
                    n.text = etree.CDATA(compile_expr(n.text, inherit_vars))


def fix_rendering_context(root: etree._ElementTree, outside_vars, inside_vars):
    template_nodes = set(root.xpath("descendant-or-self::*[@t-name]"))

    if template_nodes:
        for template in template_nodes:
            name = template.attrib["t-name"]
            bound_variables = collect_bound_variables(template) | set(
                outside_vars.get(name, {})
            )

            fix_template(template, bound_variables, inside_vars)

    else:
        bound_variables = collect_bound_variables(root)
        fix_template(root, bound_variables, inside_vars)


def update_template(content: str, outside_vars, inside_vars):
    # print(outside_vars)
    def callback(tree):
        fix_rendering_context(tree, outside_vars, inside_vars)

    result = update_etree(content, callback)
    result = result.replace("<![CDATA[", "").replace("]]>", "")
    result = result.replace("\u200b", "&#8203;")
    result = result.replace("&&", "&amp;&amp;")
    return result


def replace_x_path_only(content: str, variables: dict):
    def fix_xpath(root: etree._ElementTree):
        for node in root.xpath("descendant-or-self::*[@t-inherit]"):
            attr = node.get("t-inherit")
            if attr.startswith("web."):
                for xp in node.xpath("descendant-or-self::xpath[@expr]"):
                    expr = xp.get("expr")
                    if expr:
                        xp.set(
                            "expr",
                            process_xpath_expr(
                                expr, variables[attr], SKIP_XPATH_ATTRS.union({"call"})
                            ),
                        )
        return

    result = update_etree(content, fix_xpath)
    return result


def _aggregate_call_vars(root: etree._ElementTree, vars):
    # Find all nodes with t-call="sometemplate"
    for call_node in root.xpath("descendant-or-self::*[@t-call]"):
        template_name = call_node.get("t-call")
        if not template_name:
            continue

        # Ensure a set exists for this template
        var_set = vars.setdefault(template_name, set())

        # Look for t-set inside this t-call subtree
        for set_node in call_node.xpath("descendant-or-self::*[@t-set]"):
            var_name = set_node.get("t-set")
            if var_name:
                var_set.add(var_name)

    for call_node in root.xpath("descendant-or-self::*[@t-foreach]"):
        print(call_node)


def _aggregate_inside_vars(root: etree._ElementTree, inside_vars: dict[str, set[str]]):
    def _add_var(var_set, name: str | None):
        if not name:
            return
        name = name.strip()
        var_set.add(name)

    templates = root.xpath(
        "descendant-or-self::*[@t-name] | descendant-or-self::template[@id]"
    )
    for tpl in templates:
        tpl_name = tpl.get("t-name") or tpl.get("id")
        if not tpl_name:
            continue

        var_set = inside_vars.setdefault(tpl_name, set())

        # t-set introduces a local
        for set_node in tpl.xpath("descendant-or-self::*[@t-set]"):
            _add_var(var_set, set_node.get("t-set"))

        # Loops introduce locals via t-as (and maybe an index var)
        for loop_node in tpl.xpath(
            "descendant-or-self::*[@t-foreach] | descendant-or-self::*[@t-for-each]"
        ):
            _add_var(var_set, loop_node.get("t-as"))
            _add_var(
                var_set, loop_node.get("t-foreach-index") or loop_node.get("t-index")
            )


def aggregate_vars(content: str, vars={}, inside_vars={}):
    def callback(tree):
        _aggregate_call_vars(tree, vars)
        _aggregate_inside_vars(tree, inside_vars)

    update_etree(content, callback)
    return vars, inside_vars


# ------------------------------------------------------------------------------
# TESTS
# ------------------------------------------------------------------------------


def run_tests_main(test):
    # variables = test.get("inside_vars", {})
    return update_template(test["content"], {}, {})


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

# ------------------------------------------------------------------------------


def run_test_external_xpath(test):
    variables = test.get("inside_vars", {})
    return replace_x_path_only(test["content"], variables)


# Tests x-path coming from another xml file
test_external_xpath = [
    {
        "name": "x path only replace",
        "inside_vars": defaultdict(set),
        "content": """
<templates id="template" xml:space="preserve">
    <t t-name="account_accountant.AttachmentPreviewListView" t-inherit="web.ListView">
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
    <t t-name="account_accountant.AttachmentPreviewListView" t-inherit="web.ListView">
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


def run_test_vars(test):
    return update_template(test["content"], test["outside_vars"], test["inside_vars"])


test_vars = [
    {
        "name": "vars basic",
        "outside_vars": {"abc": {"a"}},
        "inside_vars": {},
        "content": '<t t-name="abc"><t t-out="a"/><t t-out="b"/></t>',
        "expected": '<t t-name="abc"><t t-out="a"/><t t-out="this.b"/></t>',
    },
    {
        "name": "x path with no local vars",
        "inside_vars": defaultdict(set),
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
        "name": "x path with no local vars",
        "inside_vars": defaultdict(set),
        "outside_vars": defaultdict(set),
        "content": """
<templates id="template" xml:space="preserve">
    <t t-name="account_accountant.AttachmentPreviewListView" t-inherit="web.ListView">
        <xpath expr="//Navbar" position="attributes">
            <attribute name="setSelectedRecord.bind">setSelectedRecord</attribute>
        </xpath>
    </t>
</templates>
        """,
        "expected": """
<templates id="template" xml:space="preserve">
    <t t-name="account_accountant.AttachmentPreviewListView" t-inherit="web.ListView">
        <xpath expr="//Navbar" position="attributes">
            <attribute name="setSelectedRecord.bind">this.setSelectedRecord</attribute>
        </xpath>
    </t>
</templates>
        """,
    },
    {
        "name": "x path with local vars",
        "outside_vars": defaultdict(set),
        "inside_vars": {"web.ListView": {"item"}},
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
]


# ------------------------------------------------------------------------------

WHITELIST = []


def run_test_group(name, tests, func):
    success = 0
    fail = 0
    print(f"running suite '{name}' ({len(tests)} tests)")

    for test in tests:
        name = test.get("name")

        if WHITELIST and name not in WHITELIST:
            continue

        output = func(test)

        if output != test["expected"]:
            fail += 1
            print(f"{name}: fail")
            print("Expected:")
            print(test["expected"])
            print("Output:")
            print(output)
        else:
            success += 1

    return success, fail


if __name__ == "__main__":
    total_success = 0
    total_fail = 0

    for name, test_group, func in [
        ("main", tests, run_tests_main),
        ("xpaths", test_external_xpath, run_test_external_xpath),
        ("external vars", test_vars, run_test_vars),
    ]:
        s, f = run_test_group(name, test_group, func)
        total_success += s
        total_fail += f

    if not total_fail:
        print(f"Yep, {total_success} tests passed")
