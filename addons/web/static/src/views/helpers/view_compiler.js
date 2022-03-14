/** @odoo-module **/

import { Domain } from "@web/core/domain";
import { evaluateExpr } from "@web/core/py_js/py";
import { combineAttributes, createElement, createTextNode } from "@web/core/utils/xml";
import { Field } from "@web/fields/field";

/**
 * @typedef Compiler
 * @property {string} tag
 * @property {(el: Element, params: Record<string, any>) => Element} fn
 */

const { Component, useComponent, xml } = owl;

const templateIds = Object.create(null);

/**
 * @param {Element} parent
 * @param {Node | Node[] | void} node
 */
const append = (parent, node) => {
    if (!node) {
        return;
    }
    if (Array.isArray(node)) {
        parent.append(...node.filter(Boolean));
    } else {
        parent.append(node);
    }
};

/**
 * @param {Element} el
 * @param {string} attr
 * @param {string} string
 */
const appendAttr = (el, attr, string) => {
    const attrKey = `t-att-${attr}`;
    const attrVal = el.getAttribute(attrKey);
    el.setAttribute(attrKey, appendToStringifiedObject(attrVal, string));
};

/**
 * @param {string} originalTattr
 * @param {string} string
 * @returns {string}
 */
const appendToStringifiedObject = (originalTattr, string) => {
    const re = /{(.*)}/;
    const oldString = re.exec(originalTattr);

    if (oldString) {
        string = `${oldString[1]},${string}`;
    }
    return `{${string}}`;
};

/**
 * @param {any} invisible
 * @param {Element} compiled
 * @param {Record<string, any>} params
 * @returns {Element}
 */
const applyInvisible = (invisible, compiled, params) => {
    if (!invisible) {
        return compiled;
    }
    if (typeof invisible === "boolean" && !params.enableInvisible) {
        return;
    }
    if (!params.enableInvisible) {
        combineAttributes(
            compiled,
            "t-if",
            `!evalDomain(record,${JSON.stringify(invisible)})`,
            " and "
        );
    } else {
        let expr;
        if (Array.isArray(invisible)) {
            expr = `evalDomain(record,${JSON.stringify(invisible)})`;
        } else {
            expr = invisible;
        }
        appendAttr(compiled, "class", `o_invisible_modifier:${expr}`);
    }
    return compiled;
};

/**
 * @param {Element} el
 * @param {Element} compiled
 */
const copyAttributes = (el, compiled) => {
    if (getTagName(el) === "button") {
        return;
    }

    const isComponent = isComponentNode(compiled);
    const classes = el.className;
    if (classes) {
        compiled.classList.add(...classes.split(/\s+/).filter(Boolean));
        if (isComponent) {
            compiled.className = `'${compiled.className}'`;
        }
    }

    for (const attName of ["style", "placeholder"]) {
        let att = el.getAttribute(attName);
        if (att) {
            if (isComponent) {
                att = `'${att.replace(/'/g, "\\'")}'`;
            }
            compiled.setAttribute(attName, att);
        }
    }
};

/**
 * there is no particular expecation of what should be a boolean
 * according to a view's arch
 * Sometimes it is 0 or one, True or False ; true or false
 * @return {boolean}
 */
const evalIrUiViewModifier = (expr) => {
    if (!expr) {
        return false;
    }
    return evaluateExpr(expr, {
        true: true,
        false: false,
    });
};

/**
 * @param {Element} el
 * @param {string} modifierName
 * @returns {boolean | boolean[]}
 */
const getModifier = (el, modifierName) => {
    // AAB: I think we don't need to check attributes "invisible", "required" and "readonly"
    // directly, as the info is always put inside attribute "attrs" anyway
    // let mod = el.getAttribute(modifierName);
    // if (mod === null) {
    const modifiers = JSON.parse(el.getAttribute("modifiers") || "{}");
    const mod = modifierName in modifiers ? modifiers[modifierName] : false;
    // }
    // AAB: is this necessary for modifiers?
    // if (!Array.isArray(mod) && !(typeof mod === "boolean")) {
    //     mod = !!evalIrUiViewModifier(mod);
    // }
    return Array.isArray(mod) ? mod : !!mod; // convert 1/0 to true/false
};

/**
 * @param {any} node
 * @returns {string}
 */
const getTagName = (node) => (node.tagName || "").toLowerCase();

/**
 * @param {any} node
 * @returns {string}
 */
const getTitleTagName = (node) => getTagName(node)[0].toUpperCase() + getTagName(node).slice(1);

/**
 * @param {Element} compiled
 * @param {Record<string, any>} params
 */
const handleEmpty = (compiled, params) => {
    // handle Empty field
    if (compiled.nodeName === "label") {
        const tAttClass = `o_form_label_empty:record.resId and isFieldEmpty(record,'${params.fieldName}')`;
        appendAttr(compiled, "class", tAttClass);
    }
};

/**
 * @param {Element} compiled
 * @param {Record<string, any>} params
 */
const handleInvalid = (compiled, params) => {
    // handle Invalid field
    if (compiled.nodeName === "label") {
        const tAttClass = `o_field_invalid: isFieldInvalid(record,'${params.fieldName}')`;
        appendAttr(compiled, "class", tAttClass);
    }
};

/**
 * @param {any} invisibleModifer
 * @param {{ enableInvisible?: boolean }} params
 * @returns {boolean}
 */
const isAlwaysInvisible = (invisibleModifer, params) =>
    !params.enableInvisible && typeof invisibleModifer === "boolean" && invisibleModifer;

/**
 * @param {Node} node
 * @returns {boolean}
 */
const isComment = (node) => node.nodeType === 8;

/**
 * @param {Element} el
 * @returns {boolean}
 */
const isComponentNode = (el) =>
    el.tagName === getTitleTagName(el) || (el.tagName === "t" && "t-component" in el.attributes);

/**
 * @param {Node} node
 * @returns {boolean}
 */
const isRelevantTextNode = (node) => isTextNode(node) && !!node.nodeValue.trim();

/**
 * @param {Node} node
 * @returns {boolean}
 */
const isTextNode = (node) => node.nodeType === 3;

/**
 * @returns {Element}
 */
const makeLabelTd = () => {
    const labelTd = createElement("td");
    labelTd.className = "o_td_label";
    return labelTd;
};

/**
 * @param {string} title
 * @returns {Element}
 */
const makeSeparator = (title) => {
    const separator = createElement("div");
    separator.className = "o_horizontal_separator";
    separator.textContent = title;
    return separator;
};

export class ViewCompiler {
    constructor(activeFields) {
        /** @type {Record<string, any>} */
        this.activeFields = activeFields;
        /** @type {number} */
        this.id = 1;
        /** @type {Record<string, Element[]>} */
        this.labels = {};
        /** @type {Compiler[]} */
        this.compilers = [];
    }

    /**
     * @param {Element} xmlElement
     * @param {Record<string, any>} params
     * @returns {Element}
     */
    compile(xmlElement, params = {}) {
        const newRoot = createElement("t");
        const child = this.compileNode(xmlElement, params);
        append(newRoot, child);
        return newRoot;
    }

    /**
     * @param {Node} node
     * @param {Record<string, any>} params
     * @returns {Element | Text | void}
     */
    compileNode(node, params = {}) {
        if (isComment(node)) {
            return;
        }
        if (isRelevantTextNode(node)) {
            return createTextNode(node.nodeValue);
        } else if (isTextNode(node)) {
            return;
        }
        const invisible = getModifier(node, "invisible");
        if (isAlwaysInvisible(invisible, params)) {
            return;
        }

        const registryCompiler = this.compilers.find(
            (cp) => cp.tag === getTagName(node) && node.classList.contains(cp.class)
        );
        const compiler =
            (registryCompiler && registryCompiler.fn) ||
            this[`compile${getTitleTagName(node)}`] ||
            this.compileGenericNode;

        let compiledNode = compiler.call(this, node, params);
        if (compiledNode) {
            copyAttributes(node, compiledNode);
            compiledNode = applyInvisible(invisible, compiledNode, params);
        }
        return compiledNode;
    }

    /**
     * @param {string} fieldName
     * @returns {Element[]}
     */
    getLabels(fieldName) {
        const labels = this.labels[fieldName] || [];
        this.labels[fieldName] = null;
        return labels;
    }

    /**
     * @param {Element} el
     * @param {Record<string, any>} params
     * @returns {Element}
     */
    makeFieldLabel(el, params) {
        let label = createElement("label");
        label.className = "o_form_label";
        const fieldName = el.getAttribute("name");

        label = applyInvisible(getModifier(el, "invisible"), label, params);
        this.pushLabel(fieldName, label);
        return label;
    }

    /**
     * @param {string} fieldName
     * @param {Element} label
     */
    pushLabel(fieldName, label) {
        this.labels[fieldName] = this.labels[fieldName] || [];
        this.labels[fieldName].push(label);
    }

    // ------------------------------------------------------------------------
    // Compilers
    // ------------------------------------------------------------------------

    /**
     * @param {Element} el
     * @param {Record<string, any>} params
     * @returns {Element}
     */
    compileButton(el, params) {
        const button = createElement("ViewButton", { record: "record" });

        // Props
        const clickParams = {};
        const owlAttributes = ["t-if"];
        const stringPropsAttributes = ["string", "size", "title", "icon"];
        const clickParamsAttributes = [
            "name",
            "type",
            "args",
            "context",
            "close",
            "special",
            "effect",
            // WOWL SAD: is adding the support for debounce attribute here justified or should we
            // just override compileButton in kanban compiler to add the debounce?
            "debounce",
        ];
        for (const { name, value } of el.attributes) {
            if (owlAttributes.includes(name)) {
                button.setAttribute(name, value);
            } else if (stringPropsAttributes.includes(name)) {
                button.setAttribute(name, `'${value}'`);
            } else if (clickParamsAttributes.includes(name)) {
                clickParams[name] = value;
            }
        }
        button.setAttribute("clickParams", JSON.stringify(clickParams));
        button.setAttribute("className", `'${el.className}'`);

        // Button's body
        const buttonContent = [];
        for (const child of el.childNodes) {
            const compiled = this.compileNode(child, params);
            if (compiled) {
                buttonContent.push(compiled);
            }
        }
        if (buttonContent.length) {
            const contentSlot = createElement("t");
            contentSlot.setAttribute("t-set-slot", "contents");
            append(button, contentSlot);
            for (const buttonChild of buttonContent) {
                append(contentSlot, buttonChild);
            }
        }
        return button;
    }

    /**
     * @param {Element} el
     * @param {Record<string, any>} params
     * @returns {Element}
     */
    compileButtonBox(el, params) {
        params = Object.create(params);
        // params.enableInvisible = true; // AAB: what do we do with this? Could be useful for studio, but...
        el.classList.remove("oe_button_box");

        const buttonBox = createElement("ButtonBox");
        // because dropdown is a ul; so we need to wrap every element in a li
        // const liWrappedSlot = createElement("t");
        // liWrappedSlot.setAttribute("t-set-slot", "liWrapped");

        // if (el.children.length) {
        //     append(buttonBox, liWrappedSlot);
        // }

        for (const child of el.children) {
            append(buttonBox, this.compileNode(child, params));
            // const compiled = this.compileNode(child, params);
            // if (compiled) {
            //     const li = createElement("li");
            //     li.className = "o_dropdown_item";
            //     append(li, compiled.cloneNode(true));
            //     append(liWrappedSlot, li);
            // }
        }

        return buttonBox;
    }

    /**
     * @param {Element} el
     * @returns {Element}
     */
    compileField(el) {
        const fieldName = el.getAttribute("name");
        const fieldString = el.getAttribute("string");
        const fieldId = `field_${fieldName}_${this.id++}`;

        const field = createElement("Field");
        field.setAttribute("id", `'${fieldId}'`);
        field.setAttribute("name", `'${fieldName}'`);
        field.setAttribute("record", "record");

        // FIXME WOWL: not necessary?
        // if ("mode" in el.attributes) {
        //     const viewModes = el.getAttribute("mode").split(",");
        //     field.setAttribute("viewMode", `${JSON.stringify(viewModes)}`);
        // }

        // FIXME WOWL: only for x2many fields
        field.setAttribute(
            "archs",
            `'views' in record.fields.${fieldName} and record.fields.${fieldName}.views`
        );

        let widgetName;
        if (el.hasAttribute("widget")) {
            widgetName = el.getAttribute("widget");
            field.setAttribute("type", `'${widgetName}'`);
        }

        // handleReadonly(el, field); // AAB: done by the Field itself (s.t. it works in all views)
        handleEmpty(field, { fieldName, widgetName });

        const labels = this.getLabels(fieldName);
        for (const label of labels) {
            label.setAttribute("for", `${fieldId}`);
            if (!label.textContent) {
                if (fieldString) {
                    label.textContent = fieldString;
                } else {
                    label.setAttribute("t-esc", `record.fields.${fieldName}.string`);
                }
            }
            // handleReadonly(el, label); // AAB: seems unnecessary on labels
            handleInvalid(label, { fieldName, widgetName });
            handleEmpty(label, { fieldName, widgetName });
        }
        return field;
    }

    /**
     * @param {Element} el
     * @param {Record<string, any>} params
     * @returns {Element}
     */
    compileForm(el, params) {
        const form = createElement("div");
        form.setAttribute(
            `t-attf-class`,
            "{{props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}}"
        );
        if (params.className) {
            form.setAttribute("t-att-class", params.className);
        }
        let hasSheet = false;
        for (const child of el.childNodes) {
            hasSheet = hasSheet || getTagName(child) === "sheet";
            append(form, this.compileNode(child, params));
        }
        if (!hasSheet) {
            form.className = "o_form_nosheet";
        }
        return form;
    }

    /**
     * @param {Element} el
     * @param {Record<string, any>} params
     * @returns {Element}
     */
    compileGenericNode(el, params) {
        if (el.nodeName === "div" && el.getAttribute("name") === "button_box") {
            return this.compileButtonBox(el, params);
        }
        const compiled = createElement(el.tagName);
        const metaAttrs = ["modifiers", "attrs", "invisible", "readonly"];
        for (const attr of el.attributes) {
            if (metaAttrs.includes(attr.name)) {
                continue;
            }
            compiled.setAttribute(attr.name, attr.value);
        }
        for (const child of el.childNodes) {
            append(compiled, this.compileNode(child, params));
        }
        return compiled;
    }

    /**
     * @param {Element} el
     * @param {Record<string, any>} params
     * @returns {Element}
     */
    compileGroup(el, params) {
        let group;
        const isOuterGroup = [...el.children].some((c) => getTagName(c) === "group");
        if (isOuterGroup) {
            group = createElement("div");
            group.className = "o_group";
            if (el.hasAttribute("string")) {
                append(group, makeSeparator(el.getAttribute("string")));
            }

            const nbCols = el.hasAttribute("col")
                ? parseInt(el.getAttribute("col"), 10)
                : this.constructor.OUTER_GROUP_COL;
            const colSize = Math.max(1, Math.round(12 / nbCols));

            params = Object.create(params);
            for (const child of el.childNodes) {
                if (getTagName(child) === "newline") {
                    append(group, createElement("br"));
                    continue;
                }
                const compiled = this.compileNode(child, params);
                if (compiled && !isTextNode(compiled)) {
                    const colspan = el.hasAttribute("colspan")
                        ? parseInt(el.getAttribute("colspan"), 10)
                        : 1;
                    if (isComponentNode(compiled)) {
                        compiled.classList.add(`'o_group_col_${colSize * colspan}'`);
                    } else {
                        compiled.classList.add(`o_group_col_${colSize * colspan}`);
                    }
                    append(group, compiled);
                }
            }
        } else {
            const table = (group = createElement("table"));
            table.className = "o_group o_inner_group o_group_col_6";
            const tbody = createElement("tbody");
            append(table, tbody);

            const colAttr = el.hasAttribute("col")
                ? parseInt(el.getAttribute("col"), 10)
                : this.constructor.INNER_GROUP_COL;

            if (el.hasAttribute("string")) {
                const td = createElement("td");
                td.setAttribute("colspan", colAttr);
                td.setAttribute("style", "width: 100%");
                append(td, makeSeparator(el.getAttribute("string")));
                append(tbody, td);
            }

            const rows = [];
            let currentColspan = 0;
            let currentRow = createElement("tr");
            for (const child of el.childNodes) {
                if (isComment(child)) {
                    continue;
                }
                if (getTagName(child) === "newline") {
                    rows.push(currentRow);
                    currentRow = createElement("tr");
                    currentColspan = 0;
                    continue;
                }

                // LPE FIXME: support text here ?
                if (isRelevantTextNode(child)) {
                    continue;
                } else if (isTextNode(child)) {
                    continue;
                }

                let colspan = child.hasAttribute("colspan")
                    ? parseInt(child.getAttribute("colspan"), 10)
                    : 0;
                const isLabeledField =
                    getTagName(child) === "field" &&
                    !evalIrUiViewModifier(child.getAttribute("nolabel"));
                if (!colspan) {
                    if (isLabeledField) {
                        colspan = 2;
                    } else {
                        colspan = 1;
                    }
                }
                currentColspan += colspan;

                if (currentColspan > colAttr) {
                    rows.push(currentRow);
                    currentRow = createElement("tr");
                    currentColspan = colspan;
                }
                // LPE FIXME implem colspan brols
                //currentRow = createElement("tr");

                const tds = [];
                if (getTagName(child) === "field") {
                    if (isAlwaysInvisible(getModifier(child, "invisible"), params)) {
                        continue;
                    }

                    if (!evalIrUiViewModifier(child.getAttribute("nolabel"))) {
                        const labelTd = makeLabelTd();
                        const label = this.makeFieldLabel(child, params);
                        label.className = "o_form_label";
                        append(labelTd, label);
                        tds.push(labelTd);
                    }

                    const field = this.compileNode(child, params);
                    const fieldTd = createElement("td");
                    // LPE FIXME: convert to class ?
                    fieldTd.setAttribute("style", "width: 100%");
                    append(fieldTd, field);

                    tds.push(fieldTd);
                } else if (getTagName(child) === "label") {
                    const label = this.compileNode(child, params);
                    if (label) {
                        label.classList.add("o_form_label");
                        const labelTd = makeLabelTd();
                        append(labelTd, label);
                        tds.push(labelTd);
                    }
                } else {
                    const compiled = this.compileNode(child, params);
                    if (compiled) {
                        const td = createElement("td");
                        if (compiled.nodeType !== 3) {
                            if (compiled.classList.contains("o_td_label")) {
                                compiled.classList.remove("o_td_label");
                                td.className = "o_td_label";
                            }
                        }
                        append(td, compiled);
                        tds.push(td);
                    }
                }
                append(currentRow, tds);
            }
            if (currentRow.childNodes.length) {
                rows.push(currentRow);
            }

            append(tbody, rows);
        }
        return group;
    }

    /**
     * @param {Element} el
     * @param {Record<string, any>} params
     * @returns {Element}
     */
    compileHeader(el, params) {
        const statusBar = createElement("div");
        statusBar.className = "o_form_statusbar";
        const buttons = [];
        const others = [];
        for (const child of el.childNodes) {
            const compiled = this.compileNode(child, params);
            if (!compiled) {
                continue;
            }
            if (child.nodeName === "button") {
                buttons.push(compiled);
            } else {
                others.push(compiled);
            }
        }
        if (buttons.length) {
            const divButtons = createElement("div");
            divButtons.className = "o_statusbar_buttons";
            append(divButtons, buttons);
            append(statusBar, divButtons);
        }
        append(statusBar, others);
        return statusBar;
    }

    /**
     * @param {Element} el
     * @param {Record<string, any>} params
     * @returns {Element}
     */
    compileLabel(el, params) {
        const forAttr = el.getAttribute("for");
        // FIXME: this is the only place we use 'fields'. Maybe make it more simple?
        if (forAttr && this.activeFields[forAttr]) {
            const label = createElement("label");
            label.className = "o_form_label";
            const string = el.getAttribute("string");
            if (string) {
                label.textContent = string;
            }
            this.pushLabel(forAttr, label);
            return label;
        }
        return this.compileGenericNode(el, params);
    }

    /**
     * @param {Element} el
     * @param {Record<string, any>} params
     * @returns {Element}
     */
    compileNotebook(el, params) {
        params = Object.create(params);
        const noteBookId = `notebook_${this.id++}`;
        params.noteBookId = noteBookId;

        const headersList = createElement("ul");
        headersList.className = "nav nav-tabs";

        const contents = createElement("div");
        contents.className = "tab-content";

        const invisibleDomains = {};
        let containsAlwaysVisiblePages = false;
        for (const child of el.childNodes) {
            if (!(child instanceof Element)) {
                continue;
            }
            const page = this.compilePage(child, params);
            if (!page) {
                continue;
            }
            invisibleDomains[page.pageId] = page.invisible;
            containsAlwaysVisiblePages = containsAlwaysVisiblePages || !page.invisible;
            append(headersList, applyInvisible(page.invisible, page.header, params));
            append(contents, page.content);
        }
        if (headersList.children.length === 0) {
            return; // notebook has no visible page
        }

        let notebook = createElement("div");
        if (!containsAlwaysVisiblePages) {
            const notebookDomain = Domain.combine(Object.values(invisibleDomains), "AND");
            notebook = applyInvisible(notebookDomain.toString(), notebook, params);
        }
        notebook.classList.add("o_notebook");

        const activePage = createElement("t");
        activePage.setAttribute("t-set", noteBookId);
        activePage.setAttribute(
            "t-value",
            `state.${noteBookId} or getActivePage(record,${JSON.stringify(invisibleDomains)})`
        );
        append(notebook, activePage);

        const headers = createElement("div");
        headers.className = "o_notebook_headers";

        append(headers, headersList);
        append(notebook, headers);
        append(notebook, contents);

        return notebook;
    }

    /**
     * @param {Element} el
     * @param {Record<string, any>} params
     * @returns {{
     *  pageId: string,
     *  header: Element,
     *  content: Element,
     *  invisible: boolean | boolean[],
     * }}
     */
    compilePage(el, params) {
        const invisible = getModifier(el, "invisible");
        if (typeof invisible === "boolean" && invisible) {
            return;
        }

        const pageId = `page_${this.id++}`;
        const header = createElement("li");
        header.className = "nav-item";

        const headerLink = createElement("a");
        headerLink.className = "nav-link";
        headerLink.setAttribute("t-on-click.prevent", `()=>state.${params.noteBookId}='${pageId}'`);
        headerLink.setAttribute("href", "#");
        headerLink.setAttribute("role", "tab");
        headerLink.setAttribute(
            "t-attf-class",
            `{{${params.noteBookId}==='${pageId}'?'active':''}}`
        );
        headerLink.textContent = el.getAttribute("string") || el.getAttribute("name");
        append(header, headerLink);

        const content = createElement("div");
        content.setAttribute("t-if", `${params.noteBookId}==='${pageId}'`);
        content.className = "tab-pane active";

        for (const child of el.childNodes) {
            append(content, this.compileNode(child, params));
        }

        return { pageId, header, content, invisible };
    }

    /**
     * @param {Element} el
     * @param {Record<string, any>} params
     * @returns {Element}
     */
    compileSeparator(el, params = {}) {
        const separator = makeSeparator(el.getAttribute("string"));
        copyAttributes(el, separator);
        return applyInvisible(getModifier(el, "invisible"), separator, params);
    }

    /**
     * @param {Element} el
     * @param {Record<string, any>} params
     * @returns {Element}
     */
    compileSheet(el, params) {
        const sheetBG = createElement("div");
        sheetBG.className = "o_form_sheet_bg";

        const sheetFG = createElement("div");
        sheetFG.className = "o_form_sheet";

        append(sheetBG, sheetFG);
        for (const child of el.childNodes) {
            append(sheetFG, this.compileNode(child, params));
        }
        return sheetBG;
    }

    /**
     * @param {Element} el
     * @returns {Element}
     */
    compileWidget(el) {
        const widgetName = el.getAttribute("name");
        const tComponent = createElement("t");
        tComponent.className = "'o_widget'";
        tComponent.setAttribute("t-component", `getWidget('${widgetName}')`);
        tComponent.setAttribute("record", "record");
        tComponent.setAttribute("readonly", "props.readonly");
        return tComponent;
    }
}

/**
 * @param {typeof ViewCompiler} ViewCompiler
 * @param {string} templateKey
 * @param {Record<string, any>} activeFields
 * @param {Element} xmlDoc
 * @param {Record<string, any>} [params]
 * @returns {string}
 */
export const useViewCompiler = (ViewCompiler, templateKey, activeFields, xmlDoc, params) => {
    const component = useComponent();

    // Assigns special functions to the current component.
    Object.assign(component, {
        evalDomain(record, expr) {
            return new Domain(expr).contains(record.evalContext);
        },
        getWidget(widgetName) {
            class ToImplement extends Component {}
            ToImplement.template = xml`<div>${widgetName}</div>`;
            return ToImplement;
        },
        isFieldEmpty(record, fieldName) {
            return Field.isEmpty(record, fieldName);
        },
        isFieldInvalid(record, fieldName) {
            return record.isInvalid(fieldName);
        },
    });

    // Creates a new compiled template if the given template key hasn't been
    // compiled already.
    if (!templateIds[templateKey]) {
        const compiledDoc = new ViewCompiler(activeFields).compile(xmlDoc, params);
        templateIds[templateKey] = xml`${compiledDoc.outerHTML}`;
        // DEBUG -- start
        console.group(`Compiled template (${templateIds[templateKey]}):`);
        console.dirxml(compiledDoc);
        console.groupEnd();
        // DEBUG -- end
    }
    return templateIds[templateKey];
};

ViewCompiler.INNER_GROUP_COL = 2;
ViewCompiler.OUTER_GROUP_COL = 2;
