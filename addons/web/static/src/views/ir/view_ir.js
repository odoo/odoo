// @ts-check
/** @odoo-module native */

import { makeLogger } from "@web/core/debug/debug_logger";
import { nbsp } from "@web/core/utils/format/strings";

/**
 * @typedef {import("./view_ir_schema").ViewIRNode} ViewIRNode
 * @typedef {{ text?: (value: string) => string }} IRToElementOptions
 */

const log = makeLogger("web.view_ir");

/**
 * The arch text hook every view applies: a literal "&nbsp;" in a text node or
 * an attribute value is the non-breaking space the author meant — the same
 * rule the arch-string path applied with one replaceAll over the whole arch.
 *
 * @param {string} value
 */
export const literalNbsp = (value) => value.replaceAll("&nbsp;", nbsp);

/**
 * The two markup kinds an arch carries besides elements, named as the DOM
 * names them — the twins of `odoo.tools.view_ir.COMMENT` and
 * `PROCESSING_INSTRUCTION`. A parser walk never visits them; the materialised
 * element keeps them where the arch had them.
 */
export const COMMENT = "#comment";
export const PROCESSING_INSTRUCTION = "#pi";

/**
 * @param {{ kind: string }} node
 */
export const isMarkup = (node) =>
    node.kind === COMMENT || node.kind === PROCESSING_INSTRUCTION;

const XMLNS_NS = "http://www.w3.org/2000/xmlns/";
const XML_NS = "http://www.w3.org/XML/1998/namespace";
const CLARK = /^\{([^}]*)\}(.+)$/;

/**
 * @param {string} name
 * @returns {[string | null, string]}
 */
function splitClark(name) {
    const match = CLARK.exec(name);
    return match ? [match[1], match[2]] : [null, name];
}

/**
 * @param {Map<string, string>} prefixes
 * @param {string} uri
 * @param {string} local
 */
function qualify(prefixes, uri, local) {
    if (uri === XML_NS) {
        return `xml:${local}`;
    }
    const prefix = prefixes.get(uri);
    return prefix ? `${prefix}:${local}` : local;
}

/**
 * Materialise the DOM element the client parsers and compilers walk, from the
 * IR the server emits in `get_view()` — the twin of `odoo.tools.view_ir.to_arch`.
 *
 * @param {ViewIRNode} ir
 * @param {IRToElementOptions} [options]
 * @returns {Element}
 */
export function irToElement(ir, options = {}) {
    const end = log.perf("irToElement");
    const doc = document.implementation.createDocument(null, null, null);
    const state = { nodes: 0 };
    const element = buildElement(doc, ir, new Map(), options.text, state);
    end({ kind: ir.kind, nodes: state.nodes });
    return element;
}

/**
 * @param {XMLDocument} doc
 * @param {ViewIRNode} ir
 * @param {Map<string, string>} inherited uri -> prefix
 * @param {((value: string) => string) | undefined} text
 * @param {{ nodes: number }} state
 */
function buildElement(doc, ir, inherited, text, state) {
    state.nodes++;
    const prefixes = new Map(inherited);
    const nsmap = ir.nsmap || {};
    for (const [prefix, uri] of Object.entries(nsmap)) {
        prefixes.set(uri, prefix);
    }
    const [uri, local] = splitClark(ir.kind);
    const element = doc.createElementNS(
        uri,
        uri ? qualify(prefixes, uri, local) : local,
    );
    for (const [prefix, nsUri] of Object.entries(nsmap)) {
        element.setAttributeNS(XMLNS_NS, prefix ? `xmlns:${prefix}` : "xmlns", nsUri);
    }
    for (const [name, rawValue] of Object.entries(ir.attrs || {})) {
        const value = text ? text(rawValue) : rawValue;
        const [attrUri, attrLocal] = splitClark(name);
        if (attrUri) {
            element.setAttributeNS(
                attrUri,
                qualify(prefixes, attrUri, attrLocal),
                value,
            );
        } else {
            element.setAttribute(name, value);
        }
    }
    if (ir.text) {
        element.append(doc.createTextNode(text ? text(ir.text) : ir.text));
    }
    for (const child of ir.children || []) {
        element.append(
            child.kind === COMMENT
                ? doc.createComment(child.text || "")
                : child.kind === PROCESSING_INSTRUCTION
                  ? doc.createProcessingInstruction(
                        String(child.attrs?.target),
                        child.text || "",
                    )
                  : buildElement(doc, child, prefixes, text, state),
        );
        if (child.tail) {
            element.append(doc.createTextNode(text ? text(child.tail) : child.tail));
        }
    }
    return element;
}

/**
 * The inverse: the IR of a parsed arch element, byte-for-byte what
 * `odoo.tools.view_ir.from_arch(...).to_dict()` yields for the same XML.
 *
 * @param {Element} element
 * @returns {ViewIRNode}
 */
export function elementToIR(element) {
    const end = log.perf("elementToIR");
    const state = { nodes: 0 };
    const ir = readElement(element, state);
    end({ kind: ir.kind, nodes: state.nodes });
    return ir;
}

/**
 * @param {Element} element
 * @returns {{ attrs: Record<string, string>, nsmap: Record<string, string> }}
 */
function readAttributes(element) {
    /** @type {Record<string, string>} */
    const attrs = {};
    /** @type {Record<string, string>} */
    const nsmap = {};
    for (const attr of element.attributes) {
        if (attr.namespaceURI === XMLNS_NS) {
            nsmap[attr.prefix === "xmlns" ? attr.localName : ""] = attr.value;
        } else if (attr.namespaceURI) {
            attrs[`{${attr.namespaceURI}}${attr.localName}`] = attr.value;
        } else {
            attrs[attr.name] = attr.value;
        }
    }
    return { attrs, nsmap };
}

/**
 * The attributes of a node in either form, in document order — what a helper
 * that reads one node (a button, a widget, a view root) needs, without
 * converting the subtree under an element.
 *
 * @param {ViewIRNode | Element} node
 * @returns {Record<string, string>}
 */
export function nodeAttrs(node) {
    return "kind" in node ? node.attrs || {} : readAttributes(node).attrs;
}

/**
 * @param {Comment | ProcessingInstruction} node
 * @returns {ViewIRNode}
 */
function readMarkup(node) {
    /** @type {ViewIRNode} */
    const ir =
        node.nodeType === Node.COMMENT_NODE
            ? { kind: COMMENT }
            : {
                  kind: PROCESSING_INSTRUCTION,
                  attrs: { target: /** @type {ProcessingInstruction} */ (node).target },
              };
    if (node.data) {
        ir.text = node.data;
    }
    return ir;
}

/**
 * @param {Element} element
 * @param {{ nodes: number }} state
 * @returns {ViewIRNode}
 */
function readElement(element, state) {
    state.nodes++;
    /** @type {ViewIRNode} */
    const ir = {
        kind: element.namespaceURI
            ? `{${element.namespaceURI}}${element.localName}`
            : element.localName,
    };
    const { attrs, nsmap } = readAttributes(element);
    if (Object.keys(attrs).length) {
        ir.attrs = attrs;
    }
    let text = "";
    /** @type {ViewIRNode[]} */
    const children = [];
    /** @type {ViewIRNode | null} */
    let last = null;
    let tail = "";
    for (const node of element.childNodes) {
        if (
            node.nodeType === Node.TEXT_NODE ||
            node.nodeType === Node.CDATA_SECTION_NODE
        ) {
            if (last) {
                tail += /** @type {Text} */ (node).data;
            } else {
                text += /** @type {Text} */ (node).data;
            }
        } else if (
            node.nodeType === Node.ELEMENT_NODE ||
            node.nodeType === Node.COMMENT_NODE ||
            node.nodeType === Node.PROCESSING_INSTRUCTION_NODE
        ) {
            if (last && tail) {
                last.tail = tail;
            }
            tail = "";
            last =
                node.nodeType === Node.ELEMENT_NODE
                    ? readElement(/** @type {Element} */ (node), state)
                    : readMarkup(/** @type {Comment | ProcessingInstruction} */ (node));
            children.push(last);
        }
    }
    if (last && tail) {
        last.tail = tail;
    }
    if (text) {
        ir.text = text;
    }
    if (Object.keys(nsmap).length) {
        ir.nsmap = nsmap;
    }
    if (children.length) {
        ir.children = children;
    }
    return ir;
}
