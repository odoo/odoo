/* @odoo-module */
import { appendTo, addLegacyNodeInfo } from "./compile_lib";

function makeGroupTitleRow(node) {
    const titleDiv = this.document.createElement("div");
    titleDiv.classList.add("o_horizontal_separator");
    titleDiv.textContent = node.getAttribute("string");
    return titleDiv;
}

export function compileGroup({ document, compileNode, outerGroupCol }, { node, params }) {
    outerGroupCol = outerGroupCol || 2;

    const group = document.createElement("div");
    group.setAttribute("class", "o_group");

    if (node.hasAttribute("string")) {
        appendTo(group, makeGroupTitleRow(node));
    }

    const nbCols =
        "col" in node.attributes ? parseInt(node.getAttribute("col"), 10) : outerGroupCol;
    const colSize = Math.max(1, Math.round(12 / nbCols));

    params = Object.create(params);
    params.groupLevel = (params.groupLevel || 1) + 1;
    for (let child of node.children) {
        if (child.tagName === "newline") {
            appendTo(group, this.doc.createElement("br"));
            continue;
        }
        const compiled = compileNode(child, params);
        if (!compiled) {
            continue;
        }
        const colspan =
            "colspan" in child.attributes ? parseInt(node.getAttribute("colspan"), 10) : 1;

        compiled.classList.add(`o_group_col_${colSize * colspan}`);
        appendTo(group, compiled);
    }
    return group;
}

export function compileWidget({ document }, { node }) {
    const viewWidget = document.createElement("ViewWidget");
    viewWidget.setAttribute("model", "model");
    viewWidget.setAttribute("widgetName", `"${node.getAttribute("name")}"`);
    if ("title" in node.attributes) {
        viewWidget.setAttribute("title", `"${node.getAttribute("title")}"`);
    }
    addLegacyNodeInfo(node, viewWidget);

    return viewWidget;
}
