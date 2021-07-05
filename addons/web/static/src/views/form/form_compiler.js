/* @odoo-module */
import { evaluateExpr } from "@web/core/py_js/py";

/**
 * there is no particular expecation of what should be a boolean
 * according to a view's arch
 * Sometimes it is 0 or one, True or False ; true or false
 * @return {boolean}
 */
function evalIrUiViewModifier(expr) {
    if (!expr) {
        return false;
    }
    return evaluateExpr(expr, {
        true: true,
        false: false,
    });
}

function isTextNode(node) {
    return node.nodeType === 3;
}

function isRelevantTextNode(node) {
    return isTextNode(node) && !!node.nodeValue.trim();
}

function isComment(node) {
    return node.nodeType === 8;
}

function isComponentNode(node) {
    return node.tagName.charAt(0).toUpperCase() === node.tagName.charAt(0);
}

function appendToStringifiedObject(originalTattr, string) {
    const re = /{(.*)}/;
    const oldString = re.exec(originalTattr);

    if (oldString) {
        string = `${oldString[1]}, ${string}`;
    }
    return `{ ${string} }`;
}

function appendAttr(node, attr, string) {
    const attrKey = `t-att-${attr}`;
    const attrVal = node.getAttribute(attrKey);
    node.setAttribute(attrKey, appendToStringifiedObject(attrVal, string));
}

export class FormCompiler {
    constructor(qweb, fields) {
        this.qweb = qweb;
        this.fields = fields;
        this.parser = new DOMParser();
        this.document = this.parseXML("<templates />");
        this.id = 0;
        this.labels = {};
    }

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
        let mod = node.getAttribute(modifierName);
        if (mod === null) {
            const modifiers = this.getAllModifiers(node);
            mod = modifiers && modifierName in modifiers ? modifiers[modifierName] : null;
        }

        if (!Array.isArray(mod) && !(typeof mod === "boolean")) {
            mod = !!evalIrUiViewModifier(mod);
        }
        return mod;
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

    getInvisible(node) {
        const invisible = this.getModifier(node, "invisible");
        return invisible || false;
    }

    applyInvisible(invisible, compiled, params) {
        if (!invisible) {
            return compiled;
        }
        if (typeof invisible === "boolean" && !params.enableInvisible) {
            return;
        }
        if (!params.enableInvisible) {
            compiled.setAttribute("t-if", `!evalDomain(${JSON.stringify(invisible)})`);
        } else {
            let expr;
            if (Array.isArray(invisible)) {
                expr = `evalDomain(${JSON.stringify(invisible)})`;
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
        const invisible = this.getInvisible(node);
        if (this.isAlwaysInvisible(invisible, params)) {
            return;
        }
        const tag = node.tagName.charAt(0).toUpperCase() + node.tagName.substring(1);
        const compiler = this[`compile${tag}`];

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
        const classes = node.getAttribute("class");
        if (classes) {
            compiled.classList.add(...classes.split(" "));
        }

        const isComponent = isComponentNode(compiled);

        for (const attName of ["style", "placeholder"]) {
            let att = node.getAttribute(attName);
            if (att) {
                if (isComponent && attName === "placeholder") {
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
        const compiled = this.document.createElement(node.tagName);
        const metaAttrs = ["modifiers", "attrs", "invisible", "readonly"];
        for (const attr of node.attributes) {
            if (metaAttrs.includes(attr.name)) {
                continue;
            }
            compiled.setAttribute(attr.name, attr.value);
        }
        for (let child of node.childNodes) {
            this.append(compiled, this.compileNode(child, params));
        }
        return compiled;
    }

    compileForm(node, params) {
        const form = this.document.createElement("div");
        form.setAttribute(`class`, "o_form_view");
        form.setAttribute(
            `t-attf-class`,
            "{{props.mode === 'readonly' ? 'o_form_readonly' : 'o_form_editable'}}"
        );

        for (let child of node.childNodes) {
            const toAppend = this.compileNode(child, params);
            this.append(form, toAppend);
        }
        return form;
    }

    compileSheet(node, params) {
        const sheetBG = this.document.createElement("div");
        sheetBG.setAttribute("class", "o_form_sheet_bg");

        const sheetFG = this.document.createElement("div");
        sheetFG.setAttribute("class", "o_form_sheet");
        sheetBG.appendChild(sheetFG);
        for (let child of node.childNodes) {
            this.append(sheetFG, this.compileNode(child, params));
        }
        return sheetBG;
    }

    compileButtonBox(node, params) {
        params = Object.create(params);
        params.enableInvisible = true;

        const buttonBox = this.document.createElement("ButtonBox");
        // because dropdown is a ul; so we need to wrap every element in a li
        const liWrappedSlot = this.document.createElement("t");
        liWrappedSlot.setAttribute("t-set-slot", "liWrapped");

        if (node.children.length) {
            this.append(buttonBox, liWrappedSlot);
        }

        for (const child of node.children) {
            const compiled = this.compileNode(child, params);
            if (compiled && child.nodeName === "button") {
                compiled.classList.add("oe_stat_button");
            }
            if (compiled) {
                const li = this.document.createElement("li");
                this.append(li, compiled.cloneNode(true));
                this.append(liWrappedSlot, li);
            }

            this.append(buttonBox, compiled);
        }

        return buttonBox;
    }

    compileGroup(node, params) {
        let group;
        if (!params.isInGroup) {
            group = this.document.createElement("div");
            group.setAttribute("class", "o_group");

            if (node.hasAttribute("string")) {
                this.append(group, this.makeGroupTitleRow(node));
            }

            const nbCols = node.hasAttribute("col")
                ? parseInt(node.getAttribute("col"), 10)
                : this.constructor.OUTER_GROUP_COL;
            const colSize = Math.max(1, Math.round(12 / nbCols));

            params = Object.create(params);
            params.isInGroup = true;
            for (let child of node.childNodes) {
                if (child.tag === "newline") {
                    this.append(group, this.document.createElement("br"));
                    continue;
                }
                const compiled = this.compileNode(child, params);
                if (compiled && !isTextNode(compiled)) {
                    const colspan = node.hasAttribute("colspan")
                        ? parseInt(node.getAttribute("colspan"), 10)
                        : 1;
                    compiled.classList.add(`o_group_col_${colSize * colspan}`);
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
                this.append(td, this.makeGroupTitleRow(node));
                this.append(tbody, td);
            }

            const rows = [];
            let currentColspan = 0;
            let currentRow = this.document.createElement("tr");
            for (let child of node.childNodes) {
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
                const finalColspan = colspan - (isLabeledField ? 1 : 0);
                currentColspan += colspan;

                if (currentColspan > colAttr) {
                    rows.push(currentRow);
                    currentRow = this.document.createElement("tr");
                    currentColspan = colspan;
                }
                // LPE FIXME implem colspan brols
                //currentRow = this.document.createElement("tr");

                let tds = [];
                if (child.tagName === "field") {
                    if (this.isAlwaysInvisible(this.getInvisible(child), params)) {
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

    makeGroupTitleRow(node) {
        const titleDiv = this.document.createElement("div");
        titleDiv.classList.add("o_horizontal_separator");
        titleDiv.textContent = node.getAttribute("string");
        return titleDiv;
    }

    handleReadonly(node, compiled) {
        const readonly = this.getModifier(node, "readonly");
        if (readonly !== null) {
            const roClass = "o_readonly_modifier";
            let readonlyExpr;
            if (!Array.isArray(readonly)) {
                readonlyExpr = readonly;
            } else {
                readonlyExpr = `evalDomain(${JSON.stringify(readonly)})`;
            }
            const tAttClass = `${roClass}: ${readonlyExpr}`;
            appendAttr(compiled, "class", tAttClass);

            if (compiled.nodeName === "Field") {
                const defaultMode = compiled.getAttribute("mode") || "props.mode";
                compiled.setAttribute("mode", `${readonlyExpr} ? "readonly" : ${defaultMode}`);
            }
        }
    }

    handleRequired(node, compiled) {
        const required = this.getModifier(node, "required");
        if (required !== null) {
            const reqClass = "o_required_modifier";
            let reqExpr;
            if (!Array.isArray(required)) {
                reqExpr = required;
            } else {
                reqExpr = `evalDomain(${JSON.stringify(required)})`;
            }
            const tAttClass = `${reqClass}: ${reqExpr}`;
            appendAttr(compiled, "class", tAttClass);
        }
    }

    handleEmpty(compiled, params) {
        // handle Empty field
        let emptyClass;
        if (compiled.nodeName === "Field") {
            emptyClass = "o_field_empty";
        } else if (compiled.nodeName === "label") {
            emptyClass = "o_form_label_empty";
        }
        if (emptyClass) {
            const tAttClass = `${emptyClass}: isFieldEmpty("${params.fieldName}", "${
                params.widgetName || null
            }")`;
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

        label = this.applyInvisible(this.getInvisible(node), label, params);
        this.pushLabel(fieldName, label);
        return label;
    }

    compileLabel(node, params) {
        const forAttr = node.getAttribute("for");
        if (forAttr && this.fields.includes(forAttr)) {
            const label = this.document.createElement("label");
            const string = node.getAttribute("string");
            if (string) {
                label.textContent = string;
            }
            this.pushLabel(forAttr, label);
            return label;
        }
        return this.compileGenericNode(node, params);
    }

    compileField(node, params) {
        const field = this.document.createElement("Field");
        const fieldName = node.getAttribute("name");
        const fieldId = `field_${fieldName}_${this.id++}`;
        field.setAttribute("fieldId", `"${fieldId}"`);

        const fieldString = node.getAttribute("string");

        field.setAttribute("name", `"${fieldName}"`);
        field.setAttribute("record", `record`);
        field.setAttribute("mode", `props.mode`);

        let widgetName;
        if (node.hasAttribute("widget")) {
            widgetName = node.getAttribute("widget");
            field.setAttribute("type", `"${widgetName}"`);
        }

        this.handleReadonly(node, field);
        this.handleRequired(node, field);
        this.handleEmpty(field, { fieldName, widgetName });

        const labels = this.getLabels(fieldName);
        for (const label of labels) {
            label.setAttribute("for", `${fieldId}`);
            if (!label.textContent) {
                if (fieldString) {
                    label.textContent = fieldString;
                } else {
                    label.setAttribute("t-esc", `props.model.fields.${fieldName}.string`);
                }
            }
            this.handleReadonly(node, label);
            this.handleRequired(node, label);
            this.handleEmpty(label, { fieldName, widgetName });
        }
        return field;
    }

    compileNotebook(node, params) {
        if (params.noteBookId) {
            throw new Error("LPE FORBIDDEN");
        }
        params = Object.create(params);
        const noteBookId = `notebook_${this.id++}`;

        params.noteBookId = noteBookId;

        const notebook = this.document.createElement("div");
        notebook.classList.add("o_notebook");

        const activePage = this.document.createElement("t");
        activePage.setAttribute("t-set", noteBookId);
        notebook.appendChild(activePage);

        const headers = this.document.createElement("div");
        headers.classList.add("o_notebook_headers");
        const headersList = this.document.createElement("ul");
        headersList.classList.add("nav", "nav-tabs");
        headers.appendChild(headersList);

        notebook.appendChild(headers);

        const contents = this.document.createElement("div");
        contents.classList.add("tab-content");
        notebook.appendChild(contents);

        const invisibleDomains = {};

        for (let child of node.childNodes) {
            if (!(child instanceof Element)) {
                continue;
            }
            const page = this.compilePage(child, params);
            if (!page) {
                continue;
            }
            invisibleDomains[page.pageId] = page.invisible;
            this.append(headersList, this.applyInvisible(page.invisible, page.header, params));
            this.append(contents, page.content);
        }
        activePage.setAttribute(
            "t-value",
            `state.${noteBookId} or getActivePage(${JSON.stringify(invisibleDomains)})`
        );
        return notebook;
    }

    compilePage(node, params) {
        const invisible = this.getInvisible(node);
        if (typeof invisible === "boolean" && invisible) {
            return;
        }

        const pageId = `page_${this.id++}`;
        const header = this.document.createElement("li");
        header.classList.add("nav-item");

        const headerLink = this.document.createElement("a");
        headerLink.setAttribute("t-on-click.prevent", `state.${params.noteBookId} = "${pageId}"`);
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

        for (let child of node.childNodes) {
            this.append(content, this.compileNode(child, params));
        }

        return { pageId, header, content, invisible };
    }

    compileHeader(node, params) {
        const statusBar = this.document.createElement("div");
        statusBar.setAttribute("class", "o_form_statusbar");
        const buttons = [];
        const others = [];
        for (let child of node.childNodes) {
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
        const button = this.document.createElement("button");
        if ("string" in node.attributes) {
            button.textContent = node.getAttribute("string");
        } else if (node.childNodes.length) {
            for (const child of node.childNodes) {
                this.append(button, this.compileNode(child, params));
            }
        }

        button.classList.add("btn");

        const explicitClasses = [
            "btn-primary",
            "btn-secondary",
            "btn-link",
            "btn-success",
            "btn-info",
            "btn-warning",
            "btn-danger",
        ];

        if (!explicitClasses.some((el) => node.classList.contains(el))) {
            button.classList.add("btn-secondary");
        }

        const buttonClickParams = {};
        for (const attName of ["name", "type", "args", "context", "close", "special", "effect"]) {
            const att = node.getAttribute(attName);
            if (att) {
                buttonClickParams[attName] = att;
            }
        }
        button.setAttribute("t-on-click", `buttonClicked(${JSON.stringify(buttonClickParams)})`);
        return button;
    }

    compileWidget(node) {
        const tComponent = this.document.createElement("t");
        const widgetName = node.getAttribute("name");
        tComponent.setAttribute("t-component", `getWidget("${widgetName}")`);
        tComponent.setAttribute("record", `record`);
        tComponent.setAttribute("mode", `mode`);
        tComponent.setAttribute("t-att-class", `"o_widget"`);
        return tComponent;
    }
}
FormCompiler.INNER_GROUP_COL = 2;
FormCompiler.OUTER_GROUP_COL = 2;
