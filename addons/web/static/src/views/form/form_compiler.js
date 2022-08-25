/** @odoo-module **/

import { registry } from "@web/core/registry";
import { SIZES } from "@web/core/ui/ui_service";
import {
    append,
    combineAttributes,
    createElement,
    createTextNode,
    getTag,
} from "@web/core/utils/xml";
import { toStringExpression } from "@web/views/utils";
import {
    copyAttributes,
    getModifier,
    isAlwaysInvisible,
    isComponentNode,
    isTextNode,
    makeSeparator,
} from "@web/views/view_compiler";
import { ViewCompiler } from "../view_compiler";

const compilersRegistry = registry.category("form_compilers");

function appendAttf(el, attr, string) {
    const attrKey = `t-attf-${attr}`;
    const attrVal = el.getAttribute(attrKey);
    el.setAttribute(attrKey, appendToExpr(attrVal, string));
}

function appendToExpr(expr, string) {
    const re = /{{.*}}/;
    const oldString = re.exec(expr);
    if (oldString) {
        string = `${oldString} ${string}`;
    }
    return `{{${string} }}`;
}

/**
 * @param {Record<string, any>} obj
 * @returns {string}
 */
function objectToString(obj) {
    return `{${Object.entries(obj)
        .map((t) => t.join(":"))
        .join(",")}}`;
}

export class FormCompiler extends ViewCompiler {
    setup() {
        this.encounteredFields = {};
        /** @type {Record<string, Element[]>} */
        this.labels = {};
        this.compilers.push(
            ...compilersRegistry.getAll(),
            { selector: "div[name='button_box']", fn: this.compileButtonBox },
            { selector: "form", fn: this.compileForm },
            { selector: "group", fn: this.compileGroup },
            { selector: "header", fn: this.compileHeader },
            { selector: "label", fn: this.compileLabel },
            { selector: "notebook", fn: this.compileNotebook },
            { selector: "separator", fn: this.compileSeparator },
            { selector: "sheet", fn: this.compileSheet }
        );
    }

    compile() {
        const compiled = super.compile(...arguments);
        compiled.children[0].setAttribute("t-ref", "compiled_view_root");
        return compiled;
    }

    createLabelFromField(fieldId, fieldName, fieldString, label, params) {
        const props = {
            id: `'${fieldId}'`,
            fieldName: `'${fieldName}'`,
            record: `props.record`,
            fieldInfo: `props.archInfo.fieldNodes['${fieldId}']`,
            className: `"${label.className}"`,
        };
        let labelText = label.textContent || fieldString;
        if (label.hasAttribute("data-no-label")) {
            labelText = toStringExpression("");
        } else {
            labelText = labelText
                ? toStringExpression(labelText)
                : `props.record.fields['${fieldName}'].string`;
        }
        const formLabel = createElement("FormLabel", {
            "t-props": objectToString(props),
            string: labelText,
        });
        const condition = label.getAttribute("t-if");
        if (condition) {
            formLabel.setAttribute("t-if", condition);
        }
        return formLabel;
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
     * @param {string} fieldName
     * @param {Element} label
     */
    pushLabel(fieldName, label) {
        this.labels[fieldName] = this.labels[fieldName] || [];
        this.labels[fieldName].push(label);
    }

    //-----------------------------------------------------------------------------
    // Compilers
    //-----------------------------------------------------------------------------

    /**
     * @param {Element} el
     * @param {Record<string, any>} params
     * @returns {Element}
     */
    compileButtonBox(el, params) {
        if (!el.childNodes.length) {
            return this.compileGenericNode(el, params);
        }

        el.classList.remove("oe_button_box");
        const buttonBox = createElement("ButtonBox");
        let slotId = 0;
        let hasContent = false;
        for (const child of el.children) {
            const invisible = getModifier(child, "invisible");
            if (isAlwaysInvisible(invisible, params)) {
                continue;
            }
            hasContent = true;
            const mainSlot = createElement("t", {
                "t-set-slot": `slot_${slotId++}`,
                isVisible:
                    invisible !== false
                        ? `!evalDomainFromRecord(props.record,${JSON.stringify(invisible)})`
                        : true,
            });
            if (child.tagName === "button") {
                child.classList.add("oe_stat_button");
            }
            append(mainSlot, this.compileNode(child, params, false));
            append(buttonBox, mainSlot);
        }

        return hasContent ? buttonBox : null;
    }

    /**
     * @override
     */
    compileField(el, params) {
        const field = super.compileField(el, params);

        const fieldName = el.getAttribute("name");
        const fieldString = el.getAttribute("string");
        const fieldId = el.getAttribute("field_id") || fieldName;
        const labelsForAttr = el.getAttribute("id") || fieldId;
        const labels = this.getLabels(labelsForAttr);
        const dynamicLabel = (label) => {
            const formLabel = this.createLabelFromField(
                fieldId,
                fieldName,
                fieldString,
                label,
                params
            );
            if (formLabel) {
                label.replaceWith(formLabel);
            } else {
                label.remove();
            }
            return formLabel;
        };
        for (const label of labels) {
            dynamicLabel(label);
        }
        this.encounteredFields[fieldName] = dynamicLabel;
        return field;
    }

    /**
     * @param {Element} el
     * @param {Record<string, any>} params
     * @returns {Element}
     */
    compileForm(el, params) {
        const sheetNode = el.querySelector("sheet");
        const displayClasses = sheetNode
            ? `d-flex {{ uiService.size < ${SIZES.XXL} ? "flex-column" : "flex-nowrap h-100" }}`
            : "d-block";
        const form = createElement("div", {
            "t-att-class": "props.class",
            "t-attf-class": `{{props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}} ${displayClasses}`,
        });
        if (!sheetNode) {
            for (const child of el.childNodes) {
                append(form, this.compileNode(child, params));
            }
            form.className = "o_form_nosheet";
        } else {
            let compiledList = [];
            for (const child of el.childNodes) {
                const compiled = this.compileNode(child, params);
                if (getTag(child, true) === "sheet") {
                    append(form, compiled);
                    compiled.prepend(...compiledList);
                    compiledList = [];
                } else if (compiled) {
                    compiledList.push(compiled);
                }
            }
            append(form, compiledList);
        }
        return form;
    }

    /**
     * @param {Element} el
     * @param {Record<string, any>} params
     * @returns {Element}
     */
    compileGroup(el, params) {
        const isOuterGroup = [...el.children].some((c) => getTag(c, true) === "group");
        const formGroup = createElement(isOuterGroup ? "OuterGroup" : "InnerGroup");

        let slotId = 0;
        let sequence = 0;

        if (el.hasAttribute("col")) {
            formGroup.setAttribute("maxCols", el.getAttribute("col"));
        }

        if (el.hasAttribute("string")) {
            const titleSlot = createElement("t", { "t-set-slot": "title" }, [
                makeSeparator(el.getAttribute("string")),
            ]);
            append(formGroup, titleSlot);
        }

        let forceNewline = false;
        for (const child of el.children) {
            if (getTag(child, true) === "newline") {
                forceNewline = true;
                continue;
            }

            const invisible = getModifier(child, "invisible");
            if (isAlwaysInvisible(invisible, params)) {
                continue;
            }

            const mainSlot = createElement("t", {
                "t-set-slot": `item_${slotId++}`,
                type: "'item'",
                sequence: sequence++,
                "t-slot-scope": "scope",
            });
            let itemSpan = parseInt(child.getAttribute("colspan") || "1", 10);

            if (forceNewline) {
                mainSlot.setAttribute("newline", true);
                forceNewline = false;
            }

            let slotContent;
            if (getTag(child, true) === "field") {
                const addLabel = child.hasAttribute("nolabel")
                    ? child.getAttribute("nolabel") !== "1"
                    : true;
                slotContent = this.compileNode(child, params, false);
                if (addLabel && !isOuterGroup && !isTextNode(slotContent)) {
                    itemSpan = itemSpan === 1 ? itemSpan + 1 : itemSpan;
                    const fieldName = child.getAttribute("name");
                    const fieldId = slotContent.getAttribute("id") || fieldName;
                    const props = {
                        id: `${fieldId}`,
                        fieldName: `'${fieldName}'`,
                        record: `props.record`,
                        string: child.hasAttribute("string")
                            ? toStringExpression(child.getAttribute("string"))
                            : `props.record.fields.${fieldName}.string`,
                        fieldInfo: `props.archInfo.fieldNodes[${fieldId}]`,
                    };
                    // note: remove this oe_read/edit_only logic when form view
                    // will always be in edit mode
                    if (child.classList.contains("oe_read_only")) {
                        props.className = `'oe_read_only'`;
                    } else if (child.classList.contains("oe_edit_only")) {
                        props.className = `'oe_edit_only'`;
                    }
                    mainSlot.setAttribute("props", objectToString(props));
                    mainSlot.setAttribute("Component", "constructor.components.FormLabel");
                    mainSlot.setAttribute("subType", "'item_component'");
                }
            } else {
                if (child.classList.contains("o_td_label") || getTag(child, true) === "label") {
                    mainSlot.setAttribute("subType", "'label'");
                    child.classList.remove("o_td_label");
                }
                slotContent = this.compileNode(child, params, false);
            }

            if (slotContent && !isTextNode(slotContent)) {
                if (invisible !== false) {
                    mainSlot.setAttribute(
                        "isVisible",
                        `!evalDomainFromRecord(props.record,${JSON.stringify(invisible)})`
                    );
                }
                if (itemSpan > 0) {
                    mainSlot.setAttribute("itemSpan", `${itemSpan}`);
                }

                const groupClassExpr = `scope && scope.className`;
                if (isComponentNode(slotContent)) {
                    if (getTag(child, true) !== "button") {
                        if (slotContent.hasAttribute("class")) {
                            mainSlot.prepend(
                                createElement("t", {
                                    "t-set": "addClass",
                                    "t-value": groupClassExpr,
                                })
                            );
                            combineAttributes(
                                slotContent,
                                "class",
                                `(addClass ? " " + addClass : "")`,
                                `+`
                            );
                        } else {
                            slotContent.setAttribute("class", groupClassExpr);
                        }
                    }
                } else {
                    appendAttf(slotContent, "class", `${groupClassExpr} || ""`);
                }
                append(mainSlot, slotContent);
                append(formGroup, mainSlot);
            }
        }
        return formGroup;
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
            if (!compiled || isTextNode(compiled)) {
                continue;
            }
            if (getTag(child, true) === "field") {
                compiled.setAttribute("showTooltip", true);
                others.push(compiled);
            } else {
                if (compiled.tagName === "ViewButton") {
                    compiled.setAttribute("defaultRank", "'btn-secondary'");
                }
                buttons.push(compiled);
            }
        }
        let slotId = 0;
        const statusBarButtons = createElement("StatusBarButtons");
        statusBarButtons.setAttribute("readonly", "!props.record.isInEdition");
        for (const button of buttons) {
            const slot = createElement("t", {
                "t-set-slot": `button_${slotId++}`,
                isVisible: button.getAttribute("t-if") || true,
                displayInReadOnly:
                    button.hasAttribute("className") &&
                    button.getAttribute("className").includes("oe_read_only"),
            });
            append(slot, button);
            append(statusBarButtons, slot);
        }
        append(statusBar, statusBarButtons);
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
        // A label can contain or not the labelable Element it is referring to.
        // If it doesn't, there is no `for=`
        // Otherwise, the targetted element is somewhere else among its nextChildren
        if (forAttr) {
            let label = createElement("label");
            const string = el.getAttribute("string");
            if (string) {
                append(label, createTextNode(string));
            } else if (string === "") {
                label.setAttribute("data-no-label", "true");
            }
            if (this.encounteredFields[forAttr]) {
                label = this.encounteredFields[forAttr](label);
            } else {
                this.pushLabel(forAttr, label);
            }
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
        const noteBook = createElement("Notebook");
        const pageAnchors = [...document.querySelectorAll("[href^=\\#]")]
            .map((a) => CSS.escape(a.getAttribute("href").substring(1)))
            .filter((a) => a.length);
        const noteBookAnchors = {};

        if (el.hasAttribute("class")) {
            noteBook.setAttribute("className", toStringExpression(el.getAttribute("class")));
            el.removeAttribute("class");
        }

        for (const child of el.children) {
            if (getTag(child, true) !== "page") {
                continue;
            }
            const invisible = getModifier(child, "invisible");
            if (isAlwaysInvisible(invisible, params)) {
                continue;
            }

            const pageSlot = createElement("t");
            append(noteBook, pageSlot);

            const pageId = `page_${this.id++}`;
            const pageTitle = toStringExpression(
                child.getAttribute("string") || child.getAttribute("name") || ""
            );
            const pageNodeName = toStringExpression(child.getAttribute("name") || "");

            pageSlot.setAttribute("t-set-slot", pageId);
            pageSlot.setAttribute("title", pageTitle);
            pageSlot.setAttribute("name", pageNodeName);

            if (child.getAttribute("autofocus") === "autofocus") {
                noteBook.setAttribute("defaultPage", `"${pageId}"`);
            }

            for (const anchor of child.querySelectorAll("[href^=\\#]")) {
                const anchorValue = CSS.escape(anchor.getAttribute("href").substring(1));
                if (!anchorValue.length) {
                    continue;
                }
                pageAnchors.push(anchorValue);
                noteBookAnchors[anchorValue] = {
                    origin: `'${pageId}'`,
                };
            }

            let isVisible;
            if (invisible === false) {
                isVisible = "true";
            } else {
                isVisible = `!evalDomainFromRecord(props.record,${JSON.stringify(invisible)})`;
            }
            pageSlot.setAttribute("isVisible", isVisible);

            for (const contents of child.children) {
                append(pageSlot, this.compileNode(contents, params));
            }
        }

        if (pageAnchors.length) {
            // If anchors from the page are targetting an element
            // present in the notebook, it must be aware of the
            // page that contains the corresponding element
            for (const anchor of pageAnchors) {
                let pageId = 1;
                for (const child of el.children) {
                    if (child.querySelector(`#${anchor}`)) {
                        noteBookAnchors[anchor].target = `'page_${pageId}'`;
                        noteBookAnchors[anchor] = objectToString(noteBookAnchors[anchor]);
                        break;
                    }
                    pageId++;
                }
            }
            noteBook.setAttribute("anchors", objectToString(noteBookAnchors));
        }

        return noteBook;
    }

    /**
     * @param {Element} el
     * @param {Record<string, any>} params
     * @returns {Element}
     */
    compileSeparator(el, params = {}) {
        const separator = makeSeparator(el.getAttribute("string"));
        copyAttributes(el, separator);
        return this.applyInvisible(getModifier(el, "invisible"), separator, params);
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
        sheetFG.className = "o_form_sheet position-relative";

        append(sheetBG, sheetFG);
        for (const child of el.childNodes) {
            const compiled = this.compileNode(child, params);
            if (!compiled) {
                continue;
            }
            if (getTag(child, true) === "field") {
                compiled.setAttribute("showTooltip", true);
            }
            append(sheetFG, compiled);
        }
        return sheetBG;
    }

    /**
     * @override
     */
    compileWidget(el) {
        const widget = super.compileWidget(el);
        widget.setAttribute("readonly", `!props.record.isInEdition`);
        return widget;
    }
}
