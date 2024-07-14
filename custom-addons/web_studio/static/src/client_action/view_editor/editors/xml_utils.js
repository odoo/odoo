/** @odoo-module */
import { evaluateExpr } from "@web/core/py_js/py";
import { isComponentNode, appendAttr } from "@web/views/view_compiler";

const nodeWeak = new WeakMap();

export function countPreviousSiblings(node) {
    const countXpath = `count(preceding-sibling::${node.tagName})`;
    return node.ownerDocument.evaluate(countXpath, node, null, XPathResult.NUMBER_TYPE).numberValue;
}

export function computeXpath(node, upperBoundSelector = "form") {
    if (nodeWeak.has(node)) {
        return nodeWeak.get(node);
    }
    const tagName = node.tagName;
    const count = countPreviousSiblings(node) + 1;

    let xpath = `${tagName}[${count}]`;
    const parent = node.parentElement;
    if (!node.matches(upperBoundSelector)) {
        const parentXpath = computeXpath(parent, upperBoundSelector);
        xpath = `${parentXpath}/${xpath}`;
    } else {
        xpath = `/${xpath}`;
    }
    nodeWeak.set(node, xpath);
    return xpath;
}

export function getNodeAttributes(node) {
    const attrs = {};
    for (const att of node.getAttributeNames()) {
        if (att === "options") {
            attrs[att] = evaluateExpr(node.getAttribute(att));
            continue;
        }
        attrs[att] = node.getAttribute(att);
    }
    return attrs;
}

function getXpathNodes(xpathResult) {
    const nodes = [];
    let res;
    while ((res = xpathResult.iterateNext())) {
        nodes.push(res);
    }
    return nodes;
}

export function getNodesFromXpath(xpath, xml) {
    const owner = "evaluate" in xml ? xml : xml.ownerDocument;
    const xpathResult = owner.evaluate(xpath, xml, null, XPathResult.ORDERED_NODE_ITERATOR_TYPE);
    return getXpathNodes(xpathResult);
}

const parser = new DOMParser();
export const parseStringToXml = (str) => {
    return parser.parseFromString(str, "text/xml");
};

const serializer = new XMLSerializer();
export const serializeXmlToString = (xml) => {
    return serializer.serializeToString(xml);
};

// This function should be used in Compilers to apply the "invisible" modifiers on
// the compiled templates's nodes
export function applyInvisible(invisible, compiled, params) {
    // Just return the node if it is always Visible
    if (!invisible || invisible === "False" || invisible === "0") {
        return compiled;
    }

    let isVisileExpr;
    // If invisible is dynamic, pass a props or apply the studio class.
    if (invisible !== "True" && invisible !== "1") {
        const recordExpr = params.recordExpr || "__comp__.props.record";
        isVisileExpr = `!__comp__.evaluateBooleanExpr(${JSON.stringify(
            invisible
        )},${recordExpr}.evalContextWithVirtualIds)`;
        if (isComponentNode(compiled)) {
            compiled.setAttribute("studioIsVisible", isVisileExpr);
        } else {
            appendAttr(compiled, "class", `o_web_studio_show_invisible:!${isVisileExpr}`);
        }
    } else {
        if (isComponentNode(compiled)) {
            compiled.setAttribute("studioIsVisible", "false");
        } else {
            appendAttr(compiled, "class", `o_web_studio_show_invisible:true`);
        }
    }

    // Finally, put a t-if on the node that accounts for the parameter in the config.
    const studioShowExpr = `__comp__.viewEditorModel.showInvisible`;
    isVisileExpr = isVisileExpr ? `(${isVisileExpr} or ${studioShowExpr})` : studioShowExpr;
    if (compiled.hasAttribute("t-if")) {
        const formerTif = compiled.getAttribute("t-if");
        isVisileExpr = `( ${formerTif} ) and ${isVisileExpr}`;
    }
    compiled.setAttribute("t-if", isVisileExpr);
    return compiled;
}
