// @ts-check
/** @odoo-module native */

import { parseXML, visitXML } from "@web/core/utils/dom/xml";
import { elementToIR, isMarkup, nodeAttrs } from "@web/views/ir/view_ir";
import { processButton } from "@web/views/view_buttons";
import { Widget } from "@web/views/widgets/widget";

/** @typedef {import("@web/views/ir/view_ir_schema").ViewIRNode} ViewIRNode */

/**
 * @param {Element} node
 * @param {string} attribute
 * @returns {string}
 */
export function requiredAttribute(node, attribute) {
    const value = node.getAttribute(attribute);
    if (value === null) {
        throw new Error(
            `Arch parsing error: <${node.tagName}/> requires a "${attribute}" attribute`,
        );
    }
    return value;
}

/**
 * @param {string | null | undefined} value
 * @returns {boolean | undefined}
 */
export function staticModifier(value) {
    if (value === null || value === undefined || value === "") {
        return false;
    }
    if (value === "1" || value === "True" || value === "true") {
        return true;
    }
    if (value === "0" || value === "False" || value === "false") {
        return false;
    }
    return undefined;
}

/**
 * @param {ViewIRNode} node
 * @param {string} attribute
 * @returns {string | null}
 */
export function irAttribute(node, attribute) {
    const value = node.attrs?.[attribute];
    return value === undefined ? null : value;
}

/**
 * @param {ViewIRNode} node
 * @param {string} attribute
 * @returns {string}
 */
export function requiredIRAttribute(node, attribute) {
    const value = irAttribute(node, attribute);
    if (value === null) {
        throw new Error(
            `Arch parsing error: <${node.kind}/> requires a "${attribute}" attribute`,
        );
    }
    return value;
}

/**
 * Depth-first over an IR tree. A handler returning `false` keeps the walk out
 * of that node's children, as `visitXML` does for the element form.
 *
 * @param {ViewIRNode} ir
 * @param {(node: ViewIRNode, parent: ViewIRNode | null) => any} callback
 */
export function visitIR(ir, callback) {
    /**
     * @param {ViewIRNode} node
     * @param {ViewIRNode | null} parent
     */
    const visit = (node, parent) => {
        if (isMarkup(node)) {
            return;
        }
        if (callback(node, parent) !== false) {
            for (const child of node.children || []) {
                visit(child, node);
            }
        }
    };
    visit(ir, null);
}

/**
 * @param {ViewIRNode | Element} node
 * @returns {string}
 */
function kindOf(node) {
    return "kind" in node ? node.kind : node.tagName;
}

/**
 * @param {ViewIRNode | Element} node
 * @returns {(ViewIRNode | Element)[]}
 */
function childNodes(node) {
    return "kind" in node
        ? (node.children || []).filter((child) => !isMarkup(child))
        : [...node.children];
}

/**
 * The parent of every node in an IR tree — what a subclass that must locate
 * a node in the arch (web studio's xpath) reads, header and control children
 * included, which the parsing walk itself never descends into.
 *
 * @param {ViewIRNode} ir
 * @returns {Map<ViewIRNode, ViewIRNode | null>}
 */
export function irParents(ir) {
    /** @type {Map<ViewIRNode, ViewIRNode | null>} */
    const parents = new Map();
    visitIR(ir, (node, parent) => {
        parents.set(node, parent);
    });
    return parents;
}

export class ViewArchParser {
    /**
     * What `parse()` takes: the arch `Element` (default) or the view IR node
     * (`"ir"`). `defaultViewProps` reads this to hand over the right input.
     * @type {"element" | "ir"}
     */
    static consumes = "element";

    /**
     * Any of the three shapes an arch reaches a parser in, as the IR node.
     * The `View` hands a parser that `consumes` "ir" the node itself; a test
     * or an older caller may still pass the element or the string.
     *
     * @param {ViewIRNode | Element | string} arch
     * @returns {ViewIRNode}
     */
    toIR(arch) {
        if (typeof arch === "string") {
            return elementToIR(parseXML(arch));
        }
        return "kind" in arch ? arch : elementToIR(arch);
    }

    /**
     * @abstract
     * @param {Element} _arch
     * @param {Record<string, any>} [_models]
     * @param {string} [_modelName]
     * @returns {any}
     */
    parse(_arch, _models, _modelName) {
        throw new Error(`${this.constructor.name} must implement parse()`);
    }

    /**
     * @template {object} T
     * @param {Element} arch
     * @param {T} archInfo
     * @param {Record<string, (node: Element, archInfo: T) => any>} handlers
     * @returns {T}
     */
    visitArch(arch, archInfo, handlers) {
        visitXML(arch, (node) => {
            const handler = handlers[node.tagName];
            if (handler) {
                return handler.call(this, node, archInfo);
            }
        });
        return archInfo;
    }

    /**
     * @template {object} T
     * @param {ViewIRNode} ir
     * @param {T} archInfo
     * @param {Record<string, (node: ViewIRNode, archInfo: T) => any>} handlers
     * @returns {T}
     */
    visitIR(ir, archInfo, handlers) {
        visitIR(ir, (node) => {
            const handler = handlers[node.kind];
            if (handler) {
                return handler.call(this, node, archInfo);
            }
        });
        return archInfo;
    }

    /**
     * @param {ViewIRNode | Element} node
     * @returns {any}
     */
    processButton(node) {
        return processButton(node);
    }

    /**
     * @param {ViewIRNode | Element} node
     * @param {Record<string, any>} [_models]
     * @param {string} [_modelName]
     * @returns {any}
     */
    parseWidgetNode(node, _models, _modelName) {
        return Widget.parseWidgetNode(node);
    }

    /**
     * @param {ViewIRNode | Element} node
     * @param {number} [firstId=0]
     * @returns {any[]}
     */
    parseHeaderButtons(node, firstId = 0) {
        let id = firstId;
        return childNodes(node)
            .filter((child) => kindOf(child) === "button")
            .map((child) => ({
                ...this.processButton(child),
                type: "button",
                id: id++,
            }));
    }

    /**
     * @param {ViewIRNode | Element} node
     * @returns {any[]}
     */
    parseControls(node) {
        const controls = [];
        for (const child of childNodes(node)) {
            const attrs = nodeAttrs(child);
            switch (kindOf(child)) {
                case "button":
                    controls.push({ ...this.processButton(child), type: "button" });
                    break;
                case "create":
                    controls.push({
                        type: "create",
                        context: attrs.context ?? null,
                        string: attrs.string ?? null,
                        invisible: attrs.invisible ?? null,
                        class: attrs.class ?? null,
                    });
                    break;
                case "delete":
                    controls.push({
                        type: "delete",
                        invisible: attrs.invisible ?? null,
                    });
                    break;
            }
        }
        return controls;
    }
}
