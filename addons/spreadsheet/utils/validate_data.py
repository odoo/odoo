from collections import defaultdict
from itertools import chain
import json
import re

markdown_link_regex = r"^\[([^\[]+)\]\((.+)\)$"

xml_id_url_prefix = "odoo://ir_menu_xml_id/"

odoo_view_link_prefix = "odoo://view/"


def odoo_charts(data):
    """return all odoo chart definition in the spreadsheet"""
    figures = []
    for sheet in data.get("sheets", []):
        figures += [
            dict(figure["data"], id=figure["id"])
            for figure in sheet.get("figures", [])
            if figure["tag"] == "chart" and figure["data"]["type"].startswith("odoo_")
        ]
    return figures


def links_urls(data):
    """return all markdown links in cells"""
    urls = []
    link_prefix = "odoo://view/"
    for sheet in data.get("sheets", []):
        for cell in sheet.get("cells", {}).values():
            content = cell.get("content", "")
            match = re.match(markdown_link_regex, content)
            if match and match.group(2).startswith(link_prefix):
                urls.append(match.group(2))
    return urls


def odoo_view_links(data):
    """return all view definitions embedded in link cells.
    urls looks like odoo://view/{... view data...}
    """
    return [
        json.loads(url[len(odoo_view_link_prefix):])
        for url in links_urls(data)
        if url.startswith(odoo_view_link_prefix)
    ]


def remove_aggregator(field_name):
    """remove the group operator
    >>> remove_aggregator("amount:sum")
    >>> "amount"
    """
    return field_name.split(":")[0]


def domain_fields(domain):
    """return all field names used in the domain"""
    fields = []
    for leaf in domain:
        if len(leaf) == 3:
            fields.append(leaf[0])
    return fields


def pivot_measure_fields(pivot):
    measures = [
        measure if isinstance(measure, str)
        # "field" has been renamed to "name"
        else measure["field"] if "field" in measure
        else measure["name"]
        for measure in pivot["measures"]
    ]
    return [
        measure
        for measure in measures
        if measure != "__count"
    ]


def pivot_fields(pivot):
    """return all field names used in a pivot definition"""
    model = pivot["model"]
    fields = set(
        # colGroupBys and rowGroupBys were renamed to columns and rows
        pivot.get("colGroupBys", []) + [col["name"] for col in pivot.get("columns", [])]
        + pivot.get("rowGroupBys", []) + [row["name"] for row in pivot.get("rows", [])]
        + pivot_measure_fields(pivot)
        + domain_fields(pivot["domain"])
    )
    measure = pivot.get("sortedColumn") and pivot["sortedColumn"]["measure"]
    if measure and measure != "__count":
        fields.add(measure)
    return model, fields


def list_order_fields(list_definition):
    return [order["name"] for order in list_definition["orderBy"]]


def list_fields(list_definition):
    """return all field names used in a list definitions"""
    model = list_definition["model"]
    fields = set(
        list_definition["columns"]
        + list_order_fields(list_definition)
        + domain_fields(list_definition["domain"])
    )
    return model, fields


def chart_fields(chart):
    """return all field names used in a chart definitions"""
    model = chart["metaData"]["resModel"]
    fields = set(
        chart["metaData"]["groupBy"]
        + chart["searchParams"]["groupBy"]
        + domain_fields(chart["searchParams"]["domain"])
    )
    measure = chart["metaData"]["measure"]
    if measure != "__count":
        fields.add(measure)
    return model, fields


def filter_fields(data):
    """return all field names used in global filter definitions"""
    fields_by_model = defaultdict(set)
    charts = odoo_charts(data)
    odoo_version = data.get("odooVersion", 1)
    if odoo_version < 5:
        for filter_definition in data.get("globalFilters", []):
            for pivot_id, matching in filter_definition.get("pivotFields", dict()).items():
                model = data["pivots"][pivot_id]["model"]
                fields_by_model[model].add(matching["field"])
            for list_id, matching in filter_definition.get("listFields", dict()).items():
                model = data["lists"][list_id]["model"]
                fields_by_model[model].add(matching["field"])
            for chart_id, matching in filter_definition.get("graphFields", dict()).items():
                chart = next((chart for chart in charts if chart["id"] == chart_id), None)
                model = chart["metaData"]["resModel"]
                fields_by_model[model].add(matching["field"])
    else:
        for pivot in data["pivots"].values():
            model = pivot["model"]
            field = pivot.get("fieldMatching", {}).get("chain")
            if field:
                fields_by_model[model].add(field)
        for _list in data["lists"].values():
            model = _list["model"]
            field = _list.get("fieldMatching", {}).get("chain")
            if field:
                fields_by_model[model].add(field)
        for chart in charts:
            model = chart["metaData"]["resModel"]
            field = chart.get("fieldMatching", {}).get("chain")
            if field:
                fields_by_model[model].add(field)

    return dict(fields_by_model)


def odoo_view_fields(view):
    return view["action"]["modelName"], set(domain_fields(view["action"]["domain"]))


def extract_fields(extract_fn, items):
    fields_by_model = defaultdict(set)
    for item in items:
        model, fields = extract_fn(item)
        fields_by_model[model] |= {remove_aggregator(field) for field in fields}
    return dict(fields_by_model)


def fields_in_spreadsheet(data):
    """return all fields, grouped by model, used in the spreadsheet"""
    all_fields = chain(
        extract_fields(list_fields, data.get("lists", dict()).values()).items(),
        extract_fields(pivot_fields, data.get("pivots", dict()).values()).items(),
        extract_fields(chart_fields, odoo_charts(data)).items(),
        extract_fields(odoo_view_fields, odoo_view_links(data)).items(),
        filter_fields(data).items(),
    )
    fields_by_model = defaultdict(set)
    for model, fields in all_fields:
        fields_by_model[model] |= fields
    return dict(fields_by_model)


def menus_xml_ids_in_spreadsheet(data):

    return set(data.get("chartOdooMenusReferences", {}).values()) | {
        url[len(xml_id_url_prefix):]
        for url in links_urls(data)
        if url.startswith(xml_id_url_prefix)
    }
