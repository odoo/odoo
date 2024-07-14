# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from lxml import etree, html
from lxml.html.clean import Cleaner
from psycopg2 import OperationalError
from itertools import groupby
from collections import defaultdict

from odoo import http, _, Command, models
from odoo.http import request, serialize_exception
from odoo.addons.web_studio.controllers import main
from odoo.tools.safe_eval import safe_eval

# We are dealing with an HTML document that has QWeb syntax in it (<t />, t-att etc..)
# in addition to some attributes that are specific to the reportEditor (oe-..., ws-...)
# We cannot use the tools.mail cleaner for that.
html_cleaner = Cleaner(safe_attrs_only=False, remove_unknown_tags=False)
def html_to_xml_tree(stringHTML):
    temp = html.fromstring(stringHTML)
    temp = _cleanup_from_client(temp)
    html_cleaner(temp)
    return temp

def _group_t_call_content(t_call_node):
    """Groups the content of a t_call_node according to whether they are "real" (div, h2 etc...)
    or mere <t t-set="" />. In the QWeb semantics the former will form the content inserted
    in place of the <t t-out="0" /> nodes.

    param etree.Element t_call_node: a node that is of the form <t t-call="sometemplace">....</t>

    returns dict:
        {
            [call_group_key: str]: {
                "nodes": list[etree.Element],
                "are_real": bool,
            }
        }
    """
    node_groups = {}
    for index, (k, g) in enumerate(groupby(t_call_node.iterchildren(etree.Element), key=lambda n: bool(n.get("t-set")))):
        node_groups[str(index + 1)] = {
            "nodes": list(g),
            "are_real": not k,
        }
    return node_groups

def _collect_t_call_content(tree):
    """Collect every node that has a t-call attribute in tree and their content in an object.
    Each node is assigned an ID that will be necessary in def _recompose_arch_with_t_call_parts.
    Since the report editor inlines the t-calls and puts their content in the t-row="0" of the called
    template, we endup with some pieces of view scattered everywhere.
    This function prepares the battlefield by identifying nodes that belong to a certain original tree

    param etree.Element tree: the root element of a tree.

    returns dict:
        {
            [call_key: str]: {
                "node": etree.Element,
                "content": dict (see def _group_t_call_content)
            }
        }
    """
    t_calls = {}
    t_call_nodes = [tree] if tree.get("t-call") else []
    for index, tcall in enumerate(t_call_nodes + tree.findall(".//*[@t-call]")):
        call_key = str(index+1)
        tcall.set("ws-call-key", call_key)
        t_calls[call_key] = {
            "node": tcall,
            "content": _group_t_call_content(tcall),
        }
    return t_calls

def _recompose_arch_with_t_call_parts(main_tree, origin_call_groups, changed_call_groups):
    """Reciprocal to def _collect_t_call_content. Except each TCallGroup's content may have
    changed. In the main_tree, which has been cleaned from all its t-call contents, append either
    the content that has changed, or the original one.

    param etree.Element main_tree: a tree which t-call do not have children, and must have ids
    param dict origin_call_groups: see def _collect_t_call_content
    param dict changed_call_groups: see def _collect_t_call_content
    """
    for call_key in sorted(origin_call_groups.keys(), key=int):
        origin = origin_call_groups[call_key]["content"]
        changed = changed_call_groups.get(call_key, {}).get("content")
        nodes_to_append = []

        for group_key in origin:
            if changed and changed.get(group_key):
                nodes_to_append.extend(changed[group_key]["nodes"])
            else:
                nodes_to_append.extend(origin[group_key]["nodes"])

        if nodes_to_append:
            target = main_tree.xpath(f"//t[@t-call and @ws-call-key='{call_key}']")[0]
            for n in nodes_to_append:
                target.append(etree.fromstring(etree.tostring(n)))

def api_tree_or_string(func):
    def from_tree_or_string(tree_or_string, *args, **kwargs):
        is_string = isinstance(tree_or_string, str)
        tree = html.fromstring(tree_or_string) if is_string else tree_or_string
        res = func(tree, *args, **kwargs)
        return html.tostring(res) if is_string else tree
    return from_tree_or_string

def _transform_tables(tree):
    def _transform_node(node):
        tag = node.tag
        node.set("oe-origin-tag", tag)
        node.tag = "div"
        node.set("oe-origin-style", node.attrib.pop("style", ""))

    for table in tree.iter("table"):
        should_transform = False
        table_nodes = [table]
        index = 0
        while index < len(table_nodes):
            node = table_nodes[index]
            index += 1
            if node.tag == "td":
                continue
            for child in node.iterchildren(etree.Element):
                if child.tag == "t":
                    should_transform = True
                table_nodes.append(child)
        if should_transform:
            for table_node in table_nodes:
                if table_node.tag != "t":
                    _transform_node(table_node)

@api_tree_or_string
def _html_to_client_compliant(tree):
    _transform_tables(tree)
    return tree

@api_tree_or_string
def _cleanup_from_client(tree):
    tree = _to_qweb(tree)
    for node in tree.iter(etree.Element):
        for att in ("oe-context", "oe-expression-readable"):
            node.attrib.pop(att, None)
        if node.tag == "img" and "t-att-src" in node.attrib:
            node.attrib.pop("src", None)
    return tree

@api_tree_or_string
def _to_qweb(tree):
    for el in tree.xpath("//*[@*[starts-with(name(), 'oe-origin-')]]"):
        for att in el.attrib:
            if not att.startswith("oe-origin-"):
                continue
            origin_name = att[10:]
            att_value = el.attrib.pop(att)
            if origin_name == "tag":
                el.tag = att_value
            else:
                if att_value:
                    el.set(origin_name, att_value)
                elif origin_name in el.attrib:
                    el.attrib.pop(origin_name)

    return tree

def human_readable_dotted_expr(env, model, chain):
    chain.reverse()
    human_readable = []

    while chain and model is not None:
        fname = chain.pop()
        field = model._fields[fname] if fname in model._fields else None
        if field is not None:
            human_readable.append(field.get_description(env, ["string"])["string"])
            model = env[field.comodel_name] if field.comodel_name else None
        else:
            model = None
            human_readable.append(fname.split("(")[0])

    human_readable.extend(reversed(chain))

    return human_readable

def parse_simple_dotted_expr(expr):
    parsed = []
    fn_level = 0

    single_expr = []
    for char in expr:
        if char == "." and not fn_level:
            parsed.append("".join(single_expr))
            single_expr = []
            continue

        elif char == '(':
            fn_level += 1

        elif char == ')':
            fn_level -= 1

        single_expr.append(char)

    parsed.append("".join(single_expr))

    return parsed

def expr_to_simple_chain(expr, env, main_model, qcontext):
    chain = parse_simple_dotted_expr(expr)
    if not chain:
        return ""
    model = qcontext[chain[0]] if chain[0] in qcontext else None
    if model is not None and hasattr(model, "_name") and model._name in env:
        model_description = None
        if model._name != main_model:
            model_description = env["ir.model"]._get(model._name).name
        new_chain = [model_description] if model_description else []
        new_chain.extend(human_readable_dotted_expr(env, model, chain[1:]))
        return " > ".join(new_chain) if new_chain else ""
    else:
        return ""

@api_tree_or_string
def _guess_qweb_variables(tree, report, qcontext):
    qcontext = dict(qcontext)
    keys_info = {}
    env = report.env
    qcontext["company"] = env.company
    IrQweb = env["ir.qweb"]

    def qweb_like_eval(expr, values, is_format=False):
        qcontext = {"values": values}
        if not is_format:
            compiled = IrQweb._compile_expr(expr)
        else:
            qcontext["self"] = IrQweb
            compiled = IrQweb._compile_format(expr)
        try:
            return safe_eval(compiled, qcontext)
        finally:
            env.cr.rollback()

    def qweb_like_string_eval(expr, qcontext, is_format=False):
        try:
            return qweb_like_eval(expr, qcontext, is_format) or ""
        except OperationalError:
            raise
        except Exception: # pylint: disable=W0718,W0703
            pass
        return ""

    def apply_oe_context(node, qcontext, keys_info):
        oe_context = {}
        for k, v in qcontext.items():
            try:
                if v._name in env:
                    oe_context[k] = {
                        "model":  v._name,
                        "name": env["ir.model"]._get(v._name).name,
                        "in_foreach": keys_info.get(k, {}).get("in_foreach", False)
                    }
            # Don't even warn: we just want models in the context
            # pylint: disable=W0702
            except:
                continue
        node.set("oe-context", json.dumps(oe_context))

    def recursive(node, qcontext, keys_info):
        if "t-foreach" in node.attrib:
            expr = node.get("t-foreach")
            # compile
            new_var = node.get("t-as")
            qcontext = dict(qcontext)
            keys_info = dict(keys_info)
            try:
                qcontext[new_var] = qweb_like_eval(expr, qcontext)
                keys_info[new_var] = {"in_foreach": True, "type": "python"}
            except OperationalError:
                raise
            except Exception: # pylint: disable=W0718,W0703
                pass
            apply_oe_context(node, qcontext, keys_info)

        if "t-set" in node.attrib and "t-value" in node.attrib:
            new_var = node.get("t-set")
            expr = node.get("t-value")
            try:
                evalled = qweb_like_eval(expr, qcontext)
                if new_var not in qcontext or not isinstance(evalled, type(qcontext[new_var])):
                    keys_info[new_var] = {"type": "python"}
                qcontext[new_var] = evalled
            except OperationalError:
                raise
            except Exception: # pylint: disable=W0718,W0703
                pass
            apply_oe_context(node, qcontext, keys_info)

        if "t-attf-class" in node.attrib or "t-att-class" in node.attrib:
            klass = node.get("class", "")
            node.set("oe-origin-class", klass)

            new_class = ""
            if "t-att-class" in node.attrib:
                expr = node.get("t-att-class")
                new_class += qweb_like_string_eval(expr, qcontext)

            if "t-attf-class" in node.attrib:
                expr = node.get("t-attf-class")
                new_class += qweb_like_string_eval(expr, qcontext, is_format=True)

            node.set("class", new_class)

        if "t-field" in node.attrib:
            expr = node.get("t-field")
            human_readable = expr_to_simple_chain(expr, env, report.model, qcontext) or "Field"
            node.set("oe-expression-readable", human_readable)

        tout = [att for att in ("t-out", "t-esc") if att in node.attrib]
        if tout and not node.get(tout[0]) == "0":
            expr = node.get(tout[0])
            human_readable = expr_to_simple_chain(expr, env, report.model, qcontext) or "Expression"
            node.set("oe-expression-readable", human_readable)

        if node.tag == "img" and ("t-att-src" in node.attrib):
            src = node.get("t-att-src")
            is_company_logo = src == "image_data_uri(company.logo)"
            placeholder = f'/logo.png?company={env.company.id}' if is_company_logo else'/web/static/img/placeholder.png'
            src = qweb_like_string_eval(src, qcontext) or placeholder
            node.set("src", src)

        if node.get("id") == "wrapwrap" or (node.tag == "t" and "t-name" in node.attrib):
            apply_oe_context(node, qcontext, keys_info)

        for child in node:
            recursive(child, qcontext, keys_info)

    recursive(tree, qcontext, keys_info)
    return tree

VIEW_BACKUP_KEY = "web_studio.__backup__._{view.id}_._{view.key}_"
def get_report_view_copy(view):
    key = VIEW_BACKUP_KEY.format(view=view)
    return view.with_context(active_test=False).search([("key", "=", key)], limit=1)

def _copy_report_view(view):
    copy = get_report_view_copy(view)
    if not copy:
        key = VIEW_BACKUP_KEY.format(view=view)
        copy = view.copy({
            "name": f"web_studio_backup__{view.name}",
            "inherit_id": False,
            "mode": "primary",
            "key": key,
            "active": False,
        })
    return copy

STUDIO_VIEW_KEY_TEMPLATE = "web_studio.report_editor_customization_full.view._{key}"
def _get_and_write_studio_view(view, values=None, should_create=True):
    key = STUDIO_VIEW_KEY_TEMPLATE.format(key=view.key)
    studio_view = view.with_context(active_test=False).search([("inherit_id", "=", view.id), ("key", "=", key)])

    if values is None:
        return studio_view

    if studio_view:
        vals = {"active": True, **values}
        studio_view.write(vals)
    elif should_create:
        all_inheritance = view._get_inheriting_views()
        vals = {"name": key, "key": key, "inherit_id": view.id, "mode": "extension", "priority": 9999999, **values}
        studio_view = view.create(vals)
        all_inheritance = all_inheritance.with_prefetch((all_inheritance + studio_view).ids)
        studio_view = studio_view.with_prefetch(all_inheritance._prefetch_ids)
        view._copy_field_terms_translations(all_inheritance, "arch_db", studio_view, "arch_db")

    return studio_view

class WebStudioReportController(main.WebStudioController):

    @http.route('/web_studio/create_new_report', type='json', auth='user')
    def create_new_report(self, model_name, layout, context=None):
        if context:
            request.update_context(**context)

        if layout == 'web.basic_layout':
            arch_document = etree.fromstring("""
                <t t-name="studio_report_document">
                    <div class="page"><div class="oe_structure" /></div>
                </t>
                """)
        else:
            arch_document = etree.fromstring("""
                <t t-name="studio_report_document">
                    <t t-call="%(layout)s">
                        <div class="page"><div class="oe_structure" /></div>
                    </t>
                </t>
                """ % {'layout': layout})

        view_document = request.env['ir.ui.view'].create({
            'name': 'studio_report_document',
            'type': 'qweb',
            'arch': etree.tostring(arch_document, encoding='utf-8', pretty_print=True),
        })

        new_view_document_xml_id = view_document.get_external_id()[view_document.id]
        view_document.name = '%s_document' % new_view_document_xml_id
        view_document.key = '%s_document' % new_view_document_xml_id

        if layout == 'web.basic_layout':
            arch = etree.fromstring("""
                <t t-name="studio_main_report">
                    <t t-foreach="docs" t-as="doc">
                        <t t-call="%(layout)s">
                            <t t-call="%(document)s_document"/>
                            <p style="page-break-after: always;"/>
                        </t>
                    </t>
                </t>
            """ % {'layout': layout, 'document': new_view_document_xml_id})
        else:
            arch = etree.fromstring("""
                <t t-name="studio_main_report">
                    <t t-call="web.html_container">
                        <t t-foreach="docs" t-as="doc">
                            <t t-call="%(document)s_document"/>
                        </t>
                    </t>
                </t>
            """ % {'document': new_view_document_xml_id})

        view = request.env['ir.ui.view'].create({
            'name': 'studio_main_report',
            'type': 'qweb',
            'arch': etree.tostring(arch, encoding='utf-8', pretty_print=True),
        })
        # FIXME: When website is installed, we need to set key as xmlid to search on a valid domain
        # See '_view_obj' in 'website/model/ir.ui.view'
        view.name = new_view_document_xml_id
        view.key = new_view_document_xml_id

        model = request.env['ir.model']._get(model_name)
        report = request.env['ir.actions.report'].create({
            'name': _('%s Report', model.name),
            'model': model.model,
            'report_type': 'qweb-pdf',
            'report_name': view.name,
        })
        # make it available in the print menu
        report.create_action()

        return {
            'id': report.id,
            'display_name': report.display_name,
            'report_name': report.name,
        }

    @http.route('/web_studio/print_report', type='json', auth='user')
    def print_report(self, report_id, record_id):
        report = request.env['ir.actions.report'].with_context(report_pdf_no_attachment=True, discard_logo_check=True)._get_report(report_id)
        return report.report_action(record_id)

    @http.route('/web_studio/load_report_editor', type='json', auth='user')
    def load_report_editor(self, report_id, fields, context=None):
        if context:
            request.update_context(**context)
        report = request.env['ir.actions.report'].browse(report_id)
        report_data = report.read(fields)
        paperformat = report._read_paper_format_measures()

        qweb_error = None
        try:
            report_qweb = self._get_report_qweb(report)
        except ValueError as e:
            if (hasattr(e, "context") and isinstance(e.context.get("view"), models.BaseModel)):
                # This is coming from _raise_view_error, don't crash
                report_qweb = None
                qweb_error = serialize_exception(e)
            else:
                raise e

        return {
            "report_data": report_data and report_data[0],
            "paperformat": paperformat,
            "report_qweb": report_qweb,
            "qweb_error": qweb_error,
        }

    @http.route('/web_studio/get_report_html', type='json', auth='user')
    def get_report_html(self, report_id, record_id, context=None):
        if context:
            request.update_context(**context)
        report = request.env['ir.actions.report'].browse(report_id)
        report_html = self._render_report(report, record_id)
        return report_html and report_html[0]

    @http.route('/web_studio/get_report_qweb', type='json', auth='user')
    def get_report_qweb(self, report_id, context=None):
        if context:
            request.update_context(**context)
        report = request.env['ir.actions.report'].browse(report_id)
        return self._get_report_qweb(report)

    def _get_report_qweb(self, report):
        loaded = {}
        report = report.with_context(studio=True)
        report_name = report.report_name
        IrQweb = request.env["ir.qweb"].with_context(studio=True, lang=None)
        IrView = IrQweb.env["ir.ui.view"]

        def inline_t_call(tree, variables, recursive_set):
            view_id = tree.get("ws-view-id")

            if recursive_set is None:
                recursive_set = set()

            # Collect t-calls before in an object for id assignation
            # without being polluted by the variables coming from above
            # and discrimination between real nodes and mere t-sets
            collected_t_calls = _collect_t_call_content(tree)

            # Inject t-out="0" values
            if variables and variables.get("__zero__"):
                value = variables["__zero__"]
                touts = tree.findall(".//t[@t-out='0']")
                for node in touts:
                    subtree = etree.fromstring(value)
                    for child in subtree:
                        node.append(child)
                    node.set("oe-origin-t-out", "0")
                    node.attrib.pop("t-out")

            # We want a wrapper tag around nodes that will be visible
            # on the report editor in order to insert/remove/edit nodes at the root
            # We don't want to do anything for nodes that are mere t-sets except leaving them in their group
            # Do it in opposite tree direction, to make sure we don't delete a node that still needs
            # to be treated
            for call_key, call_data in reversed(collected_t_calls.items()):
                call_node = call_data["node"]
                call_node.set("ws-view-id", view_id)
                template = call_node.get("t-call")

                if '{' in template:
                    # this t-call value is dynamic (e.g. t-call="{{company.tmp}})
                    # so its corresponding view cannot be read
                    # this template won't be returned to the Editor so it won't
                    # be customizable
                    continue
                if template in recursive_set:
                    continue

                zero = etree.Element("t", {'process_zero': "1"})
                grouped_content = call_data["content"]
                for group_key, group in grouped_content.items():
                    are_real = group.get("are_real")
                    group_element = etree.Element("t", {
                        "ws-view-id": view_id,
                        "ws-call-group-key": group_key,
                        "ws-call-key": call_key,
                    })
                    if are_real:
                        group_element.set("ws-real-children", "1")
                        zero.append(group_element)
                    else:
                        group_element.set("ws-real-children", "0")
                        call_node.append(group_element)

                    for subnode in group["nodes"]:
                        group_element.append(subnode)

                _vars = dict({} if variables is None else variables)
                if len(zero) > 0:
                    _vars["__zero__"] = etree.tostring(zero)

                new_recursive_set = set(recursive_set)
                new_recursive_set.add(template)
                sub_element = load_arch(template, _vars, new_recursive_set)
                call_node.append(sub_element)

        def load_arch(view_name, variables=None, recursive_set=None):
            if not variables:
                variables = dict()
            if view_name in loaded:
                tree = etree.fromstring(loaded[view_name])
            elif view_name == "web.external_layout":
                external_layout = "web.external_layout_standard"
                if request.env.company.external_report_layout_id:
                    external_layout = request.env.company.external_report_layout_id.sudo().key
                return load_arch(external_layout, variables, recursive_set)
            else:
                view = IrView._get(view_name)
                tree = IrQweb._get_template(view_name)[0]
                tree.set("ws-view-id", str(view.id))
                loaded[view_name] = etree.tostring(tree)
            inline_t_call(tree, variables, recursive_set)
            return tree

        main_qweb = _html_to_client_compliant(load_arch(report_name))

        with report.env.registry.cursor() as nfg_cursor:
            # We are about to evaluate expressions that may produce bad query errors
            # This new cursor isolates those evaluations from the main transaction
            # in order to avoid crashes related to them.
            report_safe_cr = report.with_env(report.env(cr=nfg_cursor))
            render_context = report_safe_cr._get_rendering_context(report_safe_cr, [0], {"studio": True})
            render_context['report_type'] = "pdf"
            main_qweb = _guess_qweb_variables(main_qweb, report_safe_cr, render_context)

        html_container = request.env["ir.ui.view"]._render_template("web.html_container", {"studio": True})
        html_container = html.fromstring(html_container)
        main_qweb.xpath("//*[@id='wrapwrap']")[0]
        wrap = html_container.xpath("//*[@id='wrapwrap']")[0]
        wrap.getparent().replace(wrap, main_qweb.xpath("//*[@id='wrapwrap']")[0])

        return html.tostring(html_container)

    def _render_report(self, report, record_id):
        return request.env['ir.actions.report'].with_context(studio=True)._render_qweb_html(report, [record_id] if record_id else [], {"studio": True})

    @http.route("/web_studio/save_report", type="json", auth="user")
    def save_report(self, report_id, report_changes=None, html_parts=None, xml_verbatim=None, record_id=None, context=None):
        if context:
            request.update_context(**context)
        report_data = None
        paperformat = None
        report = request.env["ir.actions.report"].browse(report_id)

        if report_changes:
            to_write = dict(report_changes)
            if to_write["display_in_print_menu"] is True:
                to_write["binding_model_id"] = to_write["binding_model_id"][0] if to_write["binding_model_id"] else report.model_id
            else:
                to_write["binding_model_id"] = False
            del to_write["display_in_print_menu"]

            if to_write["attachment_use"]:
                to_write["attachment"] = f"'{report.name}'"
            else:
                to_write["attachment"] = False

            to_write["paperformat_id"] = to_write["paperformat_id"][0] if to_write["paperformat_id"] else False

            to_write["groups_id"] = [Command.clear()] + [Command.link(_id) for _id in to_write["groups_id"]]
            report.write(to_write)
            report_data = report.read(to_write.keys())
            paperformat = report._read_paper_format_measures()

        IrView = request.env["ir.ui.view"].with_context(studio=True, no_cow=True, lang=None)
        xml_ids = request.env["ir.model.data"]
        if html_parts:
            for view_id, changes in html_parts.items():
                view = IrView.browse(int(view_id))
                _copy_report_view(view)
                self._handle_view_changes(view, changes)
                xml_ids = xml_ids | view.model_data_id

        if xml_verbatim:
            for view_id, arch in xml_verbatim.items():
                view = IrView.browse(int(view_id))
                _copy_report_view(view)
                view.write({"arch": arch, "active": True})
                xml_ids = xml_ids | view.model_data_id

        if report_changes or html_parts or xml_verbatim:
            xml_ids |= request.env['ir.model.data'].sudo().search(["&", ("model", "=", report._name), ("res_id", "=", report.id)])


        if xml_ids:
            xml_ids.write({"noupdate": True})

        # We always try to render the full report here because in case of failure, we need
        # the transaction to rollback
        report_html = self._render_report(report, record_id)
        report_qweb = self._get_report_qweb(report)

        return {
            "report_qweb": report_qweb,
            "report_html": report_html and report_html[0],
            "paperformat": paperformat,
            "report_data": report_data and report_data[0],
        }

    def _handle_view_changes(self, view, changes):
        """Reconciles the old view's arch and the changes and saves the result
        as an inheriting view.
        1. Mark and collect the relevant editable blocks in the old view's combined arch (essentially the t-calls contents)
        2. process the changes to convert the html they contain to xml, build the adequate object
            (see def _recompose_arch_with_t_call_parts)
        3. Decide if the main block (the root node that has not been moved around by t-call inlining) has changed
        4. Build a new tree that has the changes instead of the old version
        5. Save that tree as the arch of the inheriting view.

        param RecordSet['ir.ui.view'] view
        param changes list[dict]
            dict: {
                "type": "full" | "in_t_call",
                "call_key": str,
                "call_group_key": str,
                "html": str,
            }
        """
        old = etree.fromstring(view.get_combined_arch())

        # Collect t_call and their groups from the original view
        origin_call_groups = _collect_t_call_content(old)
        for call_data in origin_call_groups.values():
            node = call_data["node"]
            # Remove the content of each t-call
            # They will be replaced by either the changed content or the original one
            # in a following step
            for child in node:
                node.remove(child)

        changed_call_groups = defaultdict(dict)
        new_full = None
        for change in changes:
            xml = html_to_xml_tree(change["html"])
            if change["type"] == "full":
                new_full = xml
            else:
                changed_call_groups[change["call_key"]] = {
                    "content": {
                        change["call_group_key"]: {
                           "nodes": list(xml.iterchildren(etree.Element))
                        }
                    }
                }

        new_arch = new_full if new_full is not None else old
        _recompose_arch_with_t_call_parts(new_arch, origin_call_groups, changed_call_groups)
        for node in new_arch.iter(etree.Element):
            for att in ("ws-view-id", "ws-call-key", "ws-call-group-key"):
                node.attrib.pop(att, None)

        studio_view_arch = etree.Element("data")
        xpath_node = etree.Element("xpath", {"expr": f"/{old.tag}[@t-name='{old.get('t-name')}']", "position": "replace", "mode": "inner"})
        for child in new_arch:
            xpath_node.append(child)

        studio_view_arch.append(xpath_node)
        etree.indent(studio_view_arch)
        studio_view_arch = etree.tostring(studio_view_arch)

        _get_and_write_studio_view(view, {"arch": studio_view_arch})

    @http.route("/web_studio/reset_report_archs", type="json", auth="user")
    def reset_report_archs(self, report_id, include_web_layout=True):
        report = request.env["ir.actions.report"].browse(report_id)
        views = request.env["ir.ui.view"].with_context(no_primary_children=True, __views_get_original_hierarchy=[], no_cow=True).get_related_views(report.report_name, bundles=False)
        if not include_web_layout:
            views = views.filtered(lambda v: not v.key.startswith("web.") or "layout" not in v.key)
        views.reset_arch(mode="hard")

        studio_keys = [STUDIO_VIEW_KEY_TEMPLATE.format(key=v.key) for v in views]
        studio_views = request.env["ir.ui.view"].search([("inherit_id", "in", views.ids), ("key", "in", studio_keys)])
        to_deactivate = request.env["ir.ui.view"]
        for studio_view in studio_views:
            if studio_view.key == STUDIO_VIEW_KEY_TEMPLATE.format(key=studio_view.inherit_id.key):
                to_deactivate |= studio_view
        to_deactivate.write({"active": False})
        return True
