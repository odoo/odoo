/** @odoo-module **/

import { Domain } from "@web/core/domain";
import { evaluateExpr } from "@web/core/py_js/py";
import { combineAttributes } from "@web/core/utils/xml";
import { Field } from "@web/fields/field";

const { Component, useComponent, xml } = owl;

const templateIds = Object.create(null);

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

const isTextNode = (node) => {
    return node.nodeType === 3;
};

const isRelevantTextNode = (node) => {
    return isTextNode(node) && !!node.nodeValue.trim();
};

const isComment = (node) => {
    return node.nodeType === 8;
};

const isComponentNode = (node) => {
    return (
        node.tagName.charAt(0).toUpperCase() === node.tagName.charAt(0) ||
        (node.tagName === "t" && "t-component" in node.attributes)
    );
};

const appendToStringifiedObject = (originalTattr, string) => {
    const re = /{(.*)}/;
    const oldString = re.exec(originalTattr);

    if (oldString) {
        string = `${oldString[1]}, ${string}`;
    }
    return `{ ${string} }`;
};

const appendAttr = (node, attr, string) => {
    const attrKey = `t-att-${attr}`;
    const attrVal = node.getAttribute(attrKey);
    node.setAttribute(attrKey, appendToStringifiedObject(attrVal, string));
};

export class ViewCompiler {
    constructor(qweb, fields) {
        this.qweb = qweb;
        this.fields = fields;
        this.parser = new DOMParser();
        this.document = this.parseXML("<templates />");
        this.id = 0;
        this.labels = {};
        this.compilers = [];
        this.setup();
    }

    setup() {}

    parseXML(string) {
        return this.parser.parseFromString(string, "text/xml");
    }

    append(parent, node) {
        if (!node) {
            return;
        }
        if (Array.isArray(node) && node.length) {
            parent.append(...node);
        } else {
            parent.append(node);
        }
    }

    getAllModifiers(node) {
        const modifiers = node.getAttribute("modifiers");
        if (!modifiers) {
            return null;
        }
        const parsed = JSON.parse(modifiers);
        return parsed;
    }

    getModifier(node, modifierName) {
        // AAB: I think we don't need to check attributes "invisible", "required" and "readonly"
        // directly, as the info is always put inside attribute "attrs" anyway
        // let mod = node.getAttribute(modifierName);
        // if (mod === null) {
        const modifiers = JSON.parse(node.getAttribute("modifiers") || "{}");
        const mod = modifierName in modifiers ? modifiers[modifierName] : false;
        // }
        // AAB: is this necessary for modifiers?
        // if (!Array.isArray(mod) && !(typeof mod === "boolean")) {
        //     mod = !!evalIrUiViewModifier(mod);
        // }
        return Array.isArray(mod) ? mod : !!mod; // convert 1/0 to true/false
    }

    getLabels(fieldName) {
        const labels = this.labels[fieldName] || [];
        this.labels[fieldName] = null;
        return labels;
    }

    pushLabel(fieldName, label) {
        this.labels[fieldName] = this.labels[fieldName] || [];
        this.labels[fieldName].push(label);
    }

    isAlwaysInvisible(invisibleModifer, params) {
        return !params.enableInvisible && typeof invisibleModifer === "boolean" && invisibleModifer;
    }

    applyInvisible(invisible, compiled, params) {
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
            appendAttr(compiled, "class", `o_invisible_modifier: ${expr}`);
        }
        return compiled;
    }

    compile(xmlNode, params = {}) {
        const newRoot = this.document.createElement("t");
        const child = this.compileNode(xmlNode, params);
        newRoot.appendChild(child);
        return newRoot;
    }

    compileNode(node, params = {}) {
        if (isComment(node)) {
            return;
        }
        if (isRelevantTextNode(node)) {
            return this.document.createTextNode(node.nodeValue);
        } else if (isTextNode(node)) {
            return;
        }
        const invisible = this.getModifier(node, "invisible");
        if (this.isAlwaysInvisible(invisible, params)) {
            return;
        }
        const tag = node.tagName[0].toUpperCase() + node.tagName.slice(1).toLowerCase();

        const registryCompiler = this.compilers.find(
            (cp) => cp.tag === node.tagName && node.classList.contains(cp.class)
        );
        const compiler = registryCompiler ? registryCompiler.fn : this[`compile${tag}`];

        let compiledNode;
        if (compiler) {
            compiledNode = compiler.call(this, node, params);
        } else {
            compiledNode = this.compileGenericNode(node, params);
        }
        if (compiledNode) {
            this.copyAttributes(node, compiledNode);
            compiledNode = this.applyInvisible(invisible, compiledNode, params);
        }
        return compiledNode;
    }

    copyAttributes(node, compiled) {
        if (node.tagName === "button") {
            return;
        }

        const isComponent = isComponentNode(compiled);
        const classes = node.getAttribute("class");
        if (classes) {
            compiled.classList.add(...classes.split(/\s+/).filter(Boolean));
            if (isComponent) {
                compiled.className = `'${compiled.className}'`;
            }
        }

        for (const attName of ["style", "placeholder"]) {
            let att = node.getAttribute(attName);
            if (att) {
                if (isComponent) {
                    att = `"${att}"`;
                }
                compiled.setAttribute(attName, att);
            }
        }
    }

    compileGenericNode(node, params) {
        if (node.nodeName === "div" && node.getAttribute("name") === "button_box") {
            return this.compileButtonBox(node, params);
        }
        const compiled = this.document.createElement(node.tagName.toLowerCase());
        const metaAttrs = ["modifiers", "attrs", "invisible", "readonly"];
        for (const attr of node.attributes) {
            if (metaAttrs.includes(attr.name)) {
                continue;
            }
            compiled.setAttribute(attr.name, attr.value);
        }
        for (const child of node.childNodes) {
            this.append(compiled, this.compileNode(child, params));
        }
        return compiled;
    }

    compileForm(node, params) {
        const form = this.document.createElement("div");
        form.setAttribute(
            `t-attf-class`,
            "{{props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}}"
        );
        if (params.className) {
            form.setAttribute("t-att-class", params.className);
        }
        let hasSheet = false;
        for (const child of node.childNodes) {
            hasSheet = hasSheet || (child.tagName && child.tagName.toUpperCase() === "SHEET");
            const toAppend = this.compileNode(child, params);
            this.append(form, toAppend);
        }
        if (!hasSheet) {
            form.setAttribute("class", "o_form_nosheet");
        }
        return form;
    }

    compileSheet(node, params) {
        const sheetBG = this.document.createElement("div");
        sheetBG.setAttribute("class", "o_form_sheet_bg");

        const sheetFG = this.document.createElement("div");
        sheetFG.setAttribute("class", "o_form_sheet");
        sheetBG.appendChild(sheetFG);
        for (const child of node.childNodes) {
            this.append(sheetFG, this.compileNode(child, params));
        }
        return sheetBG;
    }

    compileButtonBox(node, params) {
        params = Object.create(params);
        // params.enableInvisible = true; // AAB: what do we do with this? Could be useful for studio, but...
        node.classList.remove("oe_button_box");

        const buttonBox = this.document.createElement("ButtonBox");
        // because dropdown is a ul; so we need to wrap every element in a li
        // const liWrappedSlot = this.document.createElement("t");
        // liWrappedSlot.setAttribute("t-set-slot", "liWrapped");

        // if (node.children.length) {
        //     this.append(buttonBox, liWrappedSlot);
        // }

        for (const child of node.children) {
            this.append(buttonBox, this.compileNode(child, params));
            // const compiled = this.compileNode(child, params);
            // if (compiled) {
            //     const li = this.document.createElement("li");
            //     li.classList.add("o_dropdown_item");
            //     this.append(li, compiled.cloneNode(true));
            //     this.append(liWrappedSlot, li);
            // }
        }

        return buttonBox;
    }

    compileGroup(node, params) {
        let group;
        const isOuterGroup = [...node.children].some((c) => c.tagName === "group");
        if (isOuterGroup) {
            group = this.document.createElement("div");
            group.setAttribute("class", "o_group");
            if (node.hasAttribute("string")) {
                this.append(group, this.makeSeparator(node.getAttribute("string")));
            }

            const nbCols = node.hasAttribute("col")
                ? parseInt(node.getAttribute("col"), 10)
                : this.constructor.OUTER_GROUP_COL;
            const colSize = Math.max(1, Math.round(12 / nbCols));

            params = Object.create(params);
            for (const child of node.childNodes) {
                if (child.tag === "newline") {
                    this.append(group, this.document.createElement("br"));
                    continue;
                }
                const compiled = this.compileNode(child, params);
                if (compiled && !isTextNode(compiled)) {
                    const colspan = node.hasAttribute("colspan")
                        ? parseInt(node.getAttribute("colspan"), 10)
                        : 1;
                    if (isComponentNode(compiled)) {
                        compiled.classList.add(`'o_group_col_${colSize * colspan}'`);
                    } else {
                        compiled.classList.add(`o_group_col_${colSize * colspan}`);
                    }
                    this.append(group, compiled);
                }
            }
        } else {
            const table = (group = this.document.createElement("table"));
            table.setAttribute("class", "o_group o_inner_group o_group_col_6");
            const tbody = this.document.createElement("tbody");
            table.appendChild(tbody);

            const colAttr = node.hasAttribute("col")
                ? parseInt(node.getAttribute("col"), 10)
                : this.constructor.INNER_GROUP_COL;

            if (node.hasAttribute("string")) {
                const td = this.document.createElement("td");
                td.setAttribute("colspan", colAttr);
                td.setAttribute("style", "width: 100%");
                this.append(td, this.makeSeparator(node.getAttribute("string")));
                this.append(tbody, td);
            }

            const rows = [];
            let currentColspan = 0;
            let currentRow = this.document.createElement("tr");
            for (const child of node.childNodes) {
                if (isComment(child)) {
                    continue;
                }
                if (child.tagName === "newline") {
                    rows.push(currentRow);
                    currentRow = this.document.createElement("tr");
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
                    child.tagName === "field" &&
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
                    currentRow = this.document.createElement("tr");
                    currentColspan = colspan;
                }
                // LPE FIXME implem colspan brols
                //currentRow = this.document.createElement("tr");

                const tds = [];
                if (child.tagName === "field") {
                    if (this.isAlwaysInvisible(this.getModifier(child, "invisible"), params)) {
                        continue;
                    }

                    if (!evalIrUiViewModifier(child.getAttribute("nolabel"))) {
                        const labelTd = this.makeLabelTd();
                        const label = this.makeFieldLabel(child, params);
                        label.classList.add("o_form_label");
                        this.append(labelTd, label);
                        tds.push(labelTd);
                    }

                    const field = this.compileNode(child, params);
                    const fieldTd = this.document.createElement("td");
                    // LPE FIXME: convert to class ?
                    fieldTd.setAttribute("style", "width: 100%");
                    this.append(fieldTd, field);

                    tds.push(fieldTd);
                } else if (child.tagName === "label") {
                    const label = this.compileNode(child, params);
                    if (label) {
                        label.classList.add("o_form_label");
                        const labelTd = this.makeLabelTd();
                        this.append(labelTd, label);
                        tds.push(labelTd);
                    }
                } else {
                    const compiled = this.compileNode(child, params);
                    if (compiled) {
                        const td = this.document.createElement("td");
                        if (compiled.nodeType !== 3) {
                            if (compiled.classList.contains("o_td_label")) {
                                compiled.classList.remove("o_td_label");
                                td.classList.add("o_td_label");
                            }
                        }
                        this.append(td, compiled);
                        tds.push(td);
                    }
                }
                this.append(currentRow, tds);
            }
            if (currentRow.childNodes.length) {
                rows.push(currentRow);
            }

            this.append(tbody, rows);
        }
        return group;
    }

    compileSeparator(node, params = {}) {
        const separator = this.makeSeparator(node.getAttribute("string"));
        this.copyAttributes(node, separator);
        return this.applyInvisible(this.getModifier(node, "invisible"), separator, params);
    }

    makeSeparator(title) {
        const separator = this.document.createElement("div");
        separator.classList.add("o_horizontal_separator");
        separator.textContent = title;
        return separator;
    }

    handleEmpty(compiled, params) {
        // handle Empty field
        if (compiled.nodeName === "label") {
            const tAttClass = `o_form_label_empty: record.resId and isFieldEmpty(record,"${params.fieldName}")`;
            appendAttr(compiled, "class", tAttClass);
        }
    }

    makeLabelTd() {
        const labelTd = this.document.createElement("td");
        labelTd.classList.add("o_td_label");
        return labelTd;
    }

    makeFieldLabel(node, params) {
        let label = this.document.createElement("label");
        const fieldName = node.getAttribute("name");
        label.classList.add("o_form_label");

        label = this.applyInvisible(this.getModifier(node, "invisible"), label, params);
        this.pushLabel(fieldName, label);
        return label;
    }

    compileLabel(node, params) {
        const forAttr = node.getAttribute("for");
        // FIXME: this is the only place we use 'fields'. Maybe make it more simple?
        if (forAttr && this.fields[forAttr]) {
            const label = this.document.createElement("label");
            const string = node.getAttribute("string");
            if (string) {
                label.textContent = string;
            }
            label.classList.add("o_form_label");
            this.pushLabel(forAttr, label);
            return label;
        }
        return this.compileGenericNode(node, params);
    }

    compileField(node) {
        const field = this.document.createElement("Field");
        const fieldName = node.getAttribute("name");
        const fieldId = `field_${fieldName}_${this.id++}`;
        field.setAttribute("id", `"${fieldId}"`);

        const fieldString = node.getAttribute("string");

        field.setAttribute("name", `"${fieldName}"`);
        field.setAttribute("record", `record`);

        // FIXME WOWL: not necessary?
        // if ("mode" in node.attributes) {
        //     const viewModes = node.getAttribute("mode").split(",");
        //     field.setAttribute("viewMode", `${JSON.stringify(viewModes)}`);
        // }

        // FIXME WOWL: only for x2many fields
        field.setAttribute(
            "archs",
            `"views" in props.fields.${fieldName} and props.fields.${fieldName}.views`
        );

        let widgetName;
        if (node.hasAttribute("widget")) {
            widgetName = node.getAttribute("widget");
            field.setAttribute("type", `"${widgetName}"`);
        }

        // this.handleReadonly(node, field); // AAB: done by the Field itself (s.t. it works in all views)
        // this.handleRequired(node, field); // AAB: done by the Field itself (s.t. it works in all views)
        this.handleEmpty(field, { fieldName, widgetName });

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
            // this.handleReadonly(node, label); // AAB: seems unnecessary on labels
            // this.handleRequired(node, label); // AAB: seems unnecessary on labels
            this.handleEmpty(label, { fieldName, widgetName });
        }
        return field;
    }

    compileNotebook(node, params) {
        params = Object.create(params);
        const noteBookId = `notebook_${this.id++}`;
        params.noteBookId = noteBookId;

        const headersList = this.document.createElement("ul");
        const contents = this.document.createElement("div");

        const invisibleDomains = {};
        let containsAlwaysVisiblePages = false;
        for (const child of node.childNodes) {
            if (!(child instanceof Element)) {
                continue;
            }
            const page = this.compilePage(child, params);
            if (!page) {
                continue;
            }
            invisibleDomains[page.pageId] = page.invisible;
            containsAlwaysVisiblePages = containsAlwaysVisiblePages || !page.invisible;
            this.append(headersList, this.applyInvisible(page.invisible, page.header, params));
            this.append(contents, page.content);
        }
        if (headersList.children.length === 0) {
            return; // notebook has no visible page
        }

        let notebook = this.document.createElement("div");
        if (!containsAlwaysVisiblePages) {
            const notebookDomain = Domain.combine(Object.values(invisibleDomains), "AND");
            notebook = this.applyInvisible(notebookDomain.toString(), notebook, params);
        }
        notebook.classList.add("o_notebook");

        const activePage = this.document.createElement("t");
        activePage.setAttribute("t-set", noteBookId);
        activePage.setAttribute(
            "t-value",
            `state.${noteBookId} or getActivePage(record, ${JSON.stringify(invisibleDomains)})`
        );
        notebook.appendChild(activePage);

        const headers = this.document.createElement("div");
        headers.classList.add("o_notebook_headers");
        headersList.classList.add("nav", "nav-tabs");
        headers.appendChild(headersList);
        notebook.appendChild(headers);

        contents.classList.add("tab-content");
        notebook.appendChild(contents);

        return notebook;
    }

    compilePage(node, params) {
        const invisible = this.getModifier(node, "invisible");
        if (typeof invisible === "boolean" && invisible) {
            return;
        }

        const pageId = `page_${this.id++}`;
        const header = this.document.createElement("li");
        header.classList.add("nav-item");

        const headerLink = this.document.createElement("a");
        headerLink.setAttribute(
            "t-on-click.prevent",
            `() => state.${params.noteBookId} = "${pageId}"`
        );
        headerLink.setAttribute("href", "#");
        headerLink.classList.add("nav-link");
        headerLink.setAttribute("role", "tab");
        headerLink.setAttribute(
            "t-attf-class",
            `{{ ${params.noteBookId} === "${pageId}" ? 'active' : '' }}`
        );
        headerLink.textContent = node.getAttribute("string") || node.getAttribute("name");
        header.appendChild(headerLink);

        const content = this.document.createElement("div");
        content.setAttribute("t-if", `${params.noteBookId} === "${pageId}"`);
        content.classList.add("tab-pane", "active");

        for (const child of node.childNodes) {
            this.append(content, this.compileNode(child, params));
        }

        return { pageId, header, content, invisible };
    }

    compileHeader(node, params) {
        const statusBar = this.document.createElement("div");
        statusBar.setAttribute("class", "o_form_statusbar");
        const buttons = [];
        const others = [];
        for (const child of node.childNodes) {
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
            const divButtons = this.document.createElement("div");
            divButtons.classList.add("o_statusbar_buttons");
            this.append(divButtons, buttons);
            this.append(statusBar, divButtons);
        }
        this.append(statusBar, others);
        return statusBar;
    }

    compileButton(node, params) {
        const button = this.document.createElement("ViewButton");
        // PROPS
        if ("string" in node.attributes) {
            button.setAttribute("string", `"${node.getAttribute("string")}"`);
        }
        if ("size" in node.attributes) {
            button.setAttribute("size", `"${node.getAttribute("size")}"`);
        }
        if ("title" in node.attributes) {
            button.setAttribute("title", `"${node.getAttribute("title")}"`);
        }
        if ("icon" in node.attributes) {
            button.setAttribute("icon", `"${node.getAttribute("icon")}"`);
        }
        if ("t-if" in node.attributes) {
            button.setAttribute("t-if", node.getAttribute("t-if"));
        }
        button.setAttribute("classes", JSON.stringify(Array.from(node.classList)));

        const clickParams = {};
        for (const attName of [
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
        ]) {
            const att = node.getAttribute(attName);
            if (att) {
                clickParams[attName] = att;
            }
        }
        button.setAttribute("record", "record");
        button.setAttribute("clickParams", `${JSON.stringify(clickParams)}`);

        // Button's body
        const buttonContent = [];
        for (const child of node.childNodes) {
            const compiled = this.compileNode(child, params);
            if (compiled) {
                buttonContent.push(compiled);
            }
        }
        if (buttonContent.length) {
            const contentSlot = this.document.createElement("t");
            contentSlot.setAttribute("t-set-slot", "contents");
            this.append(button, contentSlot);
            for (const buttonChild of buttonContent) {
                this.append(contentSlot, buttonChild);
            }
        }
        return button;
    }

    compileWidget(node) {
        const tComponent = this.document.createElement("t");
        const widgetName = node.getAttribute("name");
        tComponent.setAttribute("t-component", `getWidget("${widgetName}")`);
        tComponent.setAttribute("record", `record`);
        tComponent.setAttribute("readonly", `props.readonly`);
        tComponent.setAttribute("class", `"o_widget"`);
        return tComponent;
    }
}

export const useViewCompiler = (ViewCompiler, templateKey, fields, xmlDoc, params) => {
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
    });

    // Creates a new compiled template if the given template key hasn't been
    // compiled already.
    if (!templateIds[templateKey]) {
        const { qweb } = component.env;
        const compiledDoc = new ViewCompiler(qweb, fields).compile(xmlDoc, params);
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
