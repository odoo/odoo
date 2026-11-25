import { xml } from "@odoo/owl";
import { append, createElement, createTextNode, getTag } from "@web/core/utils/xml";
import { buildSpecification, parseFieldNode } from "../views/field_nodes";

/**
 * @typedef {import("../fields/field").FieldNode} FieldNode
 * @typedef {import("../views/view_models").Specification} Specification
 * @typedef {import("../views/view_models").RelatedModels} RelatedModels
 *
 * @typedef {{
 *  template: string;
 *  fieldNodes: Record<string, FieldNode>;
 *  specification: Specification;
 * }} FormArchInfo
 */

/** @type {Record<string, string>} compiled template => name of the Owl template */
const templates = Object.create(null);

/**
 * Compiles a form arch into an Owl template for the form renderer, and
 * describes the fields it displays.
 *
 * In the template, `this` is the renderer: `this.props.record` is the record,
 * and `this.props.archInfo.fieldNodes` the field nodes.
 *
 * @param {Element} arch
 * @param {{ resModel: string; relatedModels: RelatedModels }} params
 * @returns {FormArchInfo}
 */
export function compileFormArch(arch, { resModel, relatedModels }) {
    const compiler = new FormCompiler(resModel, relatedModels);
    const compiled = compiler.compileForm(arch).outerHTML;
    // `xml` creates a new Owl template on each call: the same arch reuses it
    templates[compiled] ||= xml`${compiled}`;
    const fieldNodes = compiler.fieldNodes;
    return {
        template: templates[compiled],
        fieldNodes,
        specification: buildSpecification(Object.values(fieldNodes)),
    };
}

/**
 * @param {string} str
 * @returns {string} a JS expression that evaluates to `str`
 */
function toStringExpression(str) {
    return JSON.stringify(str);
}

class FormCompiler {
    /** @type {Record<string, FieldNode>} */
    fieldNodes = {};
    /** @type {Record<string, number>} number of nodes of each field */
    fieldCounts = {};
    pageId = 0;

    /**
     * @param {string} resModel
     * @param {RelatedModels} relatedModels
     */
    constructor(resModel, relatedModels) {
        this.resModel = resModel;
        this.relatedModels = relatedModels;
    }

    /**
     * @param {Element} el
     * @returns {Element}
     */
    compileForm(el) {
        const children = [...el.childNodes];
        const sheetIndex = children.findIndex((child) => getTag(child, true) === "sheet");
        const form = createElement("div", {
            class:
                sheetIndex === -1
                    ? "o_form_renderer o_form_editable d-block o_form_nosheet"
                    : "o_form_renderer o_form_editable d-flex d-print-block flex-column",
        });
        if (sheetIndex === -1) {
            append(form, this.compileChildren(el));
            return form;
        }
        // what comes before the sheet goes in its background, above the sheet
        const sheet = this.compileSheet(children[sheetIndex]);
        sheet.prepend(...this.compileNodes(children.slice(0, sheetIndex)));
        append(form, sheet);
        append(form, this.compileNodes(children.slice(sheetIndex + 1)));
        return form;
    }

    /**
     * @param {Element} el
     * @returns {Node[]}
     */
    compileChildren(el) {
        return this.compileNodes([...el.childNodes]);
    }

    /**
     * @param {Node[]} nodes
     * @returns {Node[]}
     */
    compileNodes(nodes) {
        return nodes.map((node) => this.compileNode(node)).filter(Boolean);
    }

    /**
     * @param {Node} node
     * @returns {Node | null}
     */
    compileNode(node) {
        if (node.nodeType === Node.TEXT_NODE) {
            return createTextNode(node.textContent);
        }
        if (node.nodeType !== Node.ELEMENT_NODE) {
            return null;
        }
        const el = /** @type {Element} */ (node);
        switch (getTag(el, true)) {
            case "field":
                return this.compileField(el);
            case "group":
                return this.compileGroup(el);
            case "notebook":
                return this.compileNotebook(el);
            case "sheet":
                return this.compileSheet(el);
            default:
                return this.compileGenericNode(el);
        }
    }

    /**
     * Any other node is kept as it is, with its attributes.
     *
     * @param {Element} el
     * @returns {Element}
     */
    compileGenericNode(el) {
        const compiled = createElement(el.nodeName);
        for (const { name, value } of el.attributes) {
            compiled.setAttribute(name, value);
        }
        return append(compiled, this.compileChildren(el));
    }

    /**
     * @param {Element} el
     * @returns {Element}
     */
    compileField(el) {
        return this.createField(this.registerField(el));
    }

    /**
     * Describes a field node of the form, and gives it an id that is unique in
     * the arch: the one of its input, for its label.
     *
     * @param {Element} el
     * @returns {FieldNode}
     */
    registerField(el) {
        const node = parseFieldNode(el, this.resModel, this.relatedModels);
        node.id = `${node.name}_${(this.fieldCounts[node.name] ||= 0)}`;
        this.fieldCounts[node.name]++;
        this.fieldNodes[node.id] = node;
        return node;
    }

    /**
     * @param {FieldNode} node
     * @returns {Element}
     */
    createField(node) {
        return createElement("Field", {
            id: toStringExpression(node.id),
            record: "this.props.record",
            node: `this.props.archInfo.fieldNodes[${toStringExpression(node.id)}]`,
        });
    }

    /**
     * A group of groups is an outer group: its groups are side by side. Any
     * other group is an inner group, with a label in front of each field.
     *
     * @param {Element} el
     * @returns {Element}
     */
    compileGroup(el) {
        const isOuterGroup = [...el.children].some((child) => getTag(child, true) === "group");
        return isOuterGroup ? this.compileOuterGroup(el) : this.compileInnerGroup(el);
    }

    /**
     * @param {Element} el
     * @returns {Element}
     */
    compileOuterGroup(el) {
        const group = this.createContainer(el, "o_group row align-items-start");
        const maxCols = parseInt(el.getAttribute("col") || "2", 10);
        const colClass = `col-lg-${Math.max(1, Math.round(12 / maxCols))}`;
        for (const child of el.children) {
            const compiled = /** @type {Element | null} */ (this.compileNode(child));
            if (compiled) {
                compiled.classList.add(colClass);
                append(group, compiled);
            }
        }
        return group;
    }

    /**
     * @param {Element} el
     * @returns {Element}
     */
    compileInnerGroup(el) {
        const group = this.createContainer(el, "o_inner_group grid");
        for (const child of el.children) {
            const isLabeledField =
                getTag(child, true) === "field" &&
                !["1", "True"].includes(child.getAttribute("nolabel"));
            if (!isLabeledField) {
                const cell = createElement("div", { class: "o_cell o_cell_custom" });
                append(group, append(cell, this.compileNode(child)));
                continue;
            }
            const node = this.registerField(child);
            const field = this.createField(node);
            const labelCell = createElement(
                "div",
                { class: "o_cell o_wrap_label text-break text-900" },
                [
                    createElement("label", { class: "o_form_label", for: node.id }, [
                        createTextNode(node.string),
                    ]),
                ]
            );
            if (node.type === "boolean") {
                // the checkbox stays next to its label, also on small screens
                const inputCell = createElement("div", {
                    class: "o_cell o_no_box o_wrap_input ms-auto ms-md-0",
                });
                const wrapper = createElement("div", {
                    class: "o_wrap_field_inline d-flex d-sm-contents",
                });
                append(group, append(wrapper, [labelCell, append(inputCell, field)]));
            } else {
                const inputCell = createElement("div", { class: "o_cell o_wrap_input text-break" });
                append(group, [labelCell, append(inputCell, field)]);
            }
        }
        return group;
    }

    /**
     * @param {Element} el
     * @returns {Element}
     */
    compileNotebook(el) {
        const notebook = createElement("Notebook");
        if (el.hasAttribute("class")) {
            notebook.setAttribute("className", toStringExpression(el.getAttribute("class")));
        }
        for (const page of el.children) {
            if (getTag(page, true) !== "page") {
                continue;
            }
            const name = page.getAttribute("name") || "";
            const slot = createElement("t", {
                "t-set-slot": `page_${this.pageId++}`,
                title: toStringExpression(page.getAttribute("string") || name),
                name: toStringExpression(name),
                isVisible: "true",
            });
            if (page.hasAttribute("class")) {
                slot.setAttribute("className", toStringExpression(page.getAttribute("class")));
            }
            append(notebook, append(slot, this.compileChildren(page)));
        }
        return notebook;
    }

    /**
     * @param {Element} el
     * @returns {Element}
     */
    compileSheet(el) {
        const sheet = this.createContainer(el, "o_form_sheet position-relative");
        append(sheet, this.compileChildren(el));
        return createElement("div", { class: "o_form_sheet_bg" }, [sheet]);
    }

    /**
     * A `div` with the given classes, and the class and style of the node.
     *
     * @param {Element} el
     * @param {string} className
     * @returns {Element}
     */
    createContainer(el, className) {
        const div = createElement("div", { class: className });
        if (el.hasAttribute("class")) {
            div.setAttribute("class", `${className} ${el.getAttribute("class")}`);
        }
        if (el.hasAttribute("style")) {
            div.setAttribute("style", el.getAttribute("style"));
        }
        return div;
    }
}
