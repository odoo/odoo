// @ts-check
/** @odoo-module native */

import { registry } from "@web/core/registry";
import {
    append,
    combineAttributes,
    createElement,
    createTextNode,
    getTag,
} from "@web/core/utils/dom/xml";
import { exprToBoolean } from "@web/core/utils/format/strings";
import { SIZES } from "@web/ui/viewport";
import {
    copyAttributes,
    getModifier,
    isComponentNode,
    isTextNode,
    makeIsVisibleExpr,
    makeSeparator,
    ViewCompiler,
} from "@web/views/view_compiler";
import { toStringExpression } from "@web/views/view_utils";

const compilersRegistry = registry.category("form_compilers");

compilersRegistry.addValidation({
    selector: String,
    fn: Function,
});

function appendAttf(el, attr, string) {
    const attrKey = `t-attf-${attr}`;
    const attrVal = el.getAttribute(attrKey);
    el.setAttribute(attrKey, appendToExpr(attrVal, string));
}

export function appendToExpr(expr, string) {
    return expr ? `${expr} {{${string} }}` : `{{${string} }}`;
}

/**
 * @param {Record<string, any>} obj
 * @returns {string}
 */
export function objectToString(obj) {
    return `{${Object.entries(obj)
        .map((t) => t.join(":"))
        .join(",")}}`;
}

/**
 * @param {Element} mainSlot
 * @param {Element} slotContent
 * @param {Element} child
 */
function applyGroupItemClass(mainSlot, slotContent, child) {
    const groupClassExpr = `scope && scope.className`;
    if (!isComponentNode(slotContent)) {
        appendAttf(slotContent, "class", `${groupClassExpr} || ""`);
        return;
    }
    if (getTag(slotContent) === "FormLabel") {
        mainSlot.prepend(
            createElement("t", { "t-set": "addClass", "t-value": groupClassExpr }),
        );
        combineAttributes(
            slotContent,
            "className",
            `(addClass ? " " + addClass : "")`,
            `+`,
        );
    } else if (getTag(child, true) !== "button") {
        if (slotContent.hasAttribute("class")) {
            mainSlot.prepend(
                createElement("t", { "t-set": "addClass", "t-value": groupClassExpr }),
            );
            combineAttributes(
                slotContent,
                "class",
                `(addClass ? " " + addClass : "")`,
                `+`,
            );
        } else {
            slotContent.setAttribute("class", groupClassExpr);
        }
    }
}

export class FormCompiler extends ViewCompiler {
    /** @type {Record<string, any>} */
    encounteredFields = {};
    /** @type {Record<string, Element[] | null>} */
    labels = {};
    /** @type {number} */
    noteBookId = 0;

    setup() {
        /** @type {any} */ (this).compilers.push(
            ...compilersRegistry.getAll(),
            { selector: "div[name='button_box']", fn: this.compileButtonBox },
            { selector: "footer", fn: this.compileFooter },
            {
                selector: "form",
                fn: this.compileForm,
                doNotCopyAttributes: true,
            },
            { selector: "group", fn: this.compileGroup },
            { selector: "header", fn: this.compileHeader },
            {
                selector: "label",
                fn: this.compileLabel,
                doNotCopyAttributes: true,
            },
            { selector: "notebook", fn: this.compileNotebook },
            { selector: "setting", fn: this.compileSetting },
            { selector: "separator", fn: this.compileSeparator },
            { selector: "sheet", fn: this.compileSheet },
        );
    }

    compile(key, params = {}) {
        const compiled = super.compile(/** @type {any} */ (key), params);
        if (!params.isSubView) {
            compiled.children[0].setAttribute("t-ref", "compiled_view_root");
        }
        const sheetBG = compiled.querySelector(".o_form_sheet_bg");
        if (sheetBG) {
            sheetBG.prepend(
                createElement("div", {
                    "t-ref": "stickySentinel",
                    class: "o_form_sheet_scroll_sentinel",
                }),
            );
        }
        return compiled;
    }

    createLabelFromField(fieldId, fieldName, fieldString, label, params) {
        let labelText = label.textContent || fieldString;
        if (label.hasAttribute("data-no-label")) {
            labelText = toStringExpression("");
        } else {
            labelText = labelText
                ? toStringExpression(labelText)
                : `__comp__.props.record.fields[${toStringExpression(fieldName)}].string`;
        }
        const formLabel = createElement("FormLabel", {
            id: toStringExpression(fieldId),
            fieldName: toStringExpression(fieldName),
            record: `__comp__.props.record`,
            fieldInfo: `__comp__.props.archInfo.fieldNodes[${toStringExpression(fieldId)}]`,
            className: toStringExpression(label.className),
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

    /**
     * @param {Element} el
     * @param {Record<string, any>} params
     * @returns {Element | null}
     */
    compileButtonBox(el, params) {
        if (!el.children.length) {
            return this.compileGenericNode(el, params);
        }

        el.classList.remove("oe_button_box");
        const buttonBox = createElement("ButtonBox");
        buttonBox.setAttribute("t-if", "!__comp__.env.inDialog");
        let slotId = 0;
        let hasContent = false;
        for (const child of el.children) {
            const invisible = getModifier(child, "invisible");
            if (
                !params.compileInvisibleNodes &&
                (invisible === "True" || invisible === "1")
            ) {
                continue;
            }
            hasContent = true;
            const isVisibleExpr = makeIsVisibleExpr(invisible);
            const mainSlot = createElement("t", {
                "t-set-slot": `slot_${slotId++}`,
                isVisible: isVisibleExpr,
            });
            if (
                child.tagName === "button" ||
                (child.children.length === 1 && child.children[0].tagName === "button")
            ) {
                child.classList.add(
                    "oe_stat_button",
                    "btn",
                    "btn-outline-secondary",
                    "flex-grow-1",
                    "flex-lg-grow-0",
                );
            }
            if (child.tagName === "field") {
                child.classList.add("d-inline-block", "mb-0", "z-0");
            }
            append(mainSlot, this.compileNode(child, params, false));
            append(buttonBox, mainSlot);
        }

        return hasContent ? buttonBox : null;
    }

    /** @override */
    compileField(el, params) {
        const field = super.compileField(el, params);

        const fieldName = el.getAttribute("name");
        params.notebookPageFields?.push(fieldName);
        const fieldString = el.getAttribute("string");
        const fieldId = el.getAttribute("field_id");
        const labelsForAttr = el.getAttribute("id") || fieldName;
        const labels = this.getLabels(labelsForAttr);
        const dynamicLabel = (label) => {
            const formLabel = this.createLabelFromField(
                fieldId,
                fieldName,
                fieldString,
                label,
                {
                    ...params,
                    currentFieldArchNode: el,
                },
            );
            label.replaceWith(formLabel);
            return formLabel;
        };
        for (const label of labels) {
            dynamicLabel(label);
        }
        this.encounteredFields[fieldName] = dynamicLabel;
        if (labelsForAttr !== fieldName) {
            this.encounteredFields[labelsForAttr] = dynamicLabel;
        }
        return field;
    }

    /**
     * @param {Element} el
     * @param {Record<string, any>} params
     * @returns {Element}
     */
    compileForm(el, params) {
        let sheetNode = null;
        for (const sheet of el.querySelectorAll("sheet")) {
            if (sheet.closest("form") === el) {
                sheetNode = sheet;
                break;
            }
        }
        const displayClasses = sheetNode
            ? `d-flex d-print-block {{ __comp__.uiService.size < ${SIZES.XXL} ? "flex-column" : "flex-nowrap h-100" }}`
            : "d-block";
        const stateClasses =
            "{{ __comp__.hasUnsavedEdits() ? 'o_form_dirty' : !__comp__.props.record.isNew ? 'o_form_saved' : '' }}";
        const form = createElement("div", {
            class: "o_form_renderer",
            "t-att-class": "__comp__.props.class",
            "t-attf-class": `{{__comp__.props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}} ${displayClasses} ${stateClasses}`,
        });
        if (!sheetNode) {
            for (const child of el.childNodes) {
                const compiled = this.compileNode(
                    /** @type {Element} */ (child),
                    params,
                );
                if (!compiled || compiled.nodeName === "ButtonBox") {
                    continue;
                }
                append(form, compiled);
            }
            form.classList.add("o_form_nosheet");
        } else {
            let compiledList = [];
            for (const child of el.childNodes) {
                const compiled = this.compileNode(
                    /** @type {Element} */ (child),
                    params,
                );
                if (getTag(child, true) === "sheet") {
                    append(form, compiled);
                    /** @type {Element} */ (compiled).prepend(...compiledList);
                    compiledList = [];
                } else if (compiled && compiled.nodeName !== "ButtonBox") {
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
    compileFooter(el, params) {
        const footer = createElement("t");
        const replace = el.getAttribute("replace");
        if (replace && !exprToBoolean(replace)) {
            footer.append(
                createElement("t", {
                    "t-call": "web.DefaultButtonsSlot",
                    "t-call-context": "{ props: __comp__.props }",
                }),
            );
        }
        copyAttributes(el, footer);
        for (const child of el.childNodes) {
            const compiled = this.compileNode(/** @type {Element} */ (child), params);
            if (compiled) {
                footer.append(compiled);
            }
        }
        return footer;
    }

    /**
     * @param {Element} el
     * @param {Record<string, any>} params
     * @returns {Element}
     */
    compileGroup(el, params) {
        const isOuterGroup = [...el.children].some((c) => getTag(c, true) === "group");
        const formGroup = createElement(isOuterGroup ? "OuterGroup" : "InnerGroup");
        if (el.hasAttribute("col")) {
            formGroup.setAttribute("maxCols", el.getAttribute("col") ?? "");
        }
        if (el.hasAttribute("string")) {
            const titleSlot = createElement("t", { "t-set-slot": "title" }, [
                makeSeparator(el.getAttribute("string")),
            ]);
            append(formGroup, titleSlot);
        }
        const maxCols = Number.parseInt(formGroup.getAttribute("maxCols") || "2", 10);

        let slotId = 0;
        let sequence = 0;
        let forceNewline = false;
        for (const child of el.children) {
            if (getTag(child, true) === "newline") {
                forceNewline = true;
                continue;
            }
            const invisible = getModifier(child, "invisible");
            if (
                !params.compileInvisibleNodes &&
                (invisible === "True" || invisible === "1")
            ) {
                continue;
            }
            const mainSlot = createElement("t", {
                "t-set-slot": `item_${slotId++}`,
                type: "'item'",
                sequence: sequence++,
                "t-slot-scope": "scope",
            });
            if (forceNewline) {
                mainSlot.setAttribute("newline", "true");
                forceNewline = false;
            }
            const item = this.compileGroupItem(child, params, {
                mainSlot,
                isOuterGroup,
                maxCols,
            });
            if (!item) {
                continue;
            }
            mainSlot.setAttribute("isVisible", makeIsVisibleExpr(invisible));
            if (item.itemSpan > 0) {
                mainSlot.setAttribute("itemSpan", `${item.itemSpan}`);
            }
            applyGroupItemClass(mainSlot, item.slotContent, child);
            append(mainSlot, item.slotContent);
            append(formGroup, mainSlot);
        }
        return formGroup;
    }

    /**
     * @param {Element} child
     * @param {Record<string, any>} params
     * @param {{ mainSlot: Element, isOuterGroup: boolean, maxCols: number }} group
     * @returns {{ slotContent: Element, itemSpan: number } | null}
     */
    compileGroupItem(child, params, { mainSlot, isOuterGroup, maxCols }) {
        let itemSpan = Number.parseInt(child.getAttribute("colspan") || "1", 10);
        if (
            getTag(child, true) === "separator" ||
            child.matches("div[class='clearfix']:empty")
        ) {
            itemSpan = maxCols;
        }
        const childParams = { ...params, currentSlot: mainSlot };
        if (getTag(child, true) !== "field") {
            if (
                child.classList.contains("o_wrap_label") ||
                child.classList.contains("o_td_label") ||
                getTag(child, true) === "label"
            ) {
                mainSlot.setAttribute("subType", "'label'");
                child.classList.remove("o_wrap_label");
            }
            const slotContent = this.compileNode(child, childParams, false);
            return slotContent && !isTextNode(slotContent)
                ? { slotContent: /** @type {Element} */ (slotContent), itemSpan }
                : null;
        }
        const addLabel = child.hasAttribute("nolabel")
            ? child.getAttribute("nolabel") !== "1"
            : true;
        const slotContent = this.compileNode(child, childParams, false);
        if (!slotContent || isTextNode(slotContent)) {
            return null;
        }
        if (addLabel && !isOuterGroup) {
            itemSpan = itemSpan === 1 ? itemSpan + 1 : itemSpan;
            const fieldName = child.getAttribute("name");
            const fieldId =
                /** @type {Element} */ (slotContent).getAttribute("id") ||
                toStringExpression(fieldName);
            const props = {
                id: `${fieldId}`,
                fieldName: toStringExpression(fieldName),
                record: `__comp__.props.record`,
                string: child.hasAttribute("string")
                    ? toStringExpression(child.getAttribute("string"))
                    : `__comp__.props.record.fields[${toStringExpression(fieldName)}].string`,
                fieldInfo: `__comp__.props.archInfo.fieldNodes[${fieldId}]`,
            };
            mainSlot.setAttribute("props", objectToString(props));
            mainSlot.setAttribute(
                "Component",
                "__comp__.constructor.components.FormLabel",
            );
            mainSlot.setAttribute("subType", "'item_component'");
        }
        return { slotContent: /** @type {Element} */ (slotContent), itemSpan };
    }

    /**
     * @param {Element} el
     * @param {Record<string, any>} params
     * @returns {Element}
     */
    compileHeader(el, params) {
        const statusBar = createElement("div", {
            "t-att-class": "{ 'shadow-sm': __comp__.state.isStatusbarStickyPinned }",
        });
        statusBar.className = "o_form_statusbar d-flex justify-content-between py-2";
        const statusBarButtons = createElement("StatusBarButtons");
        const others = [];
        let slotId = 0;
        for (const child of el.childNodes) {
            if (getTag(child, true) === "separator") {
                append(
                    statusBarButtons,
                    createElement("t", {
                        "t-set-slot": `button_${slotId++}`,
                        isSeparator: "true",
                    }),
                );
                continue;
            }
            const compiled = this.compileNode(/** @type {Element} */ (child), params);
            if (!compiled || isTextNode(compiled)) {
                continue;
            }
            const compiledEl = /** @type {Element} */ (compiled);
            if (
                getTag(child, true) === "field" &&
                !(/** @type {Element} */ (child).classList.contains("btn"))
            ) {
                compiledEl.setAttribute("showTooltip", "true");
                others.push(compiled);
                continue;
            }
            if (compiledEl.tagName === "ViewButton") {
                compiledEl.setAttribute("defaultRank", "'btn-secondary'");
            }
            const slot = createElement("t", {
                "t-set-slot": `button_${slotId++}`,
                isVisible: compiledEl.getAttribute("t-if") || "true",
            });
            compiledEl.removeAttribute("t-if");
            append(slot, compiled);
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
        if (forAttr) {
            let label = createElement("label");
            copyAttributes(el, label);
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
        const res = this.compileGenericNode(el, params);
        copyAttributes(el, res);
        return res;
    }

    /**
     * @param {Element} el
     * @param {Record<string, any>} params
     * @returns {Element}
     */
    compileNotebook(el, params) {
        const noteBookId = this.noteBookId++;
        const noteBook = createElement("Notebook");

        if (el.hasAttribute("class")) {
            noteBook.setAttribute(
                "className",
                toStringExpression(el.getAttribute("class")),
            );
            el.removeAttribute("class");
        }

        noteBook.setAttribute(
            "defaultPage",
            `__comp__.props.record.isNew ? undefined : __comp__.props.activeNotebookPages[${noteBookId}]`,
        );
        noteBook.setAttribute(
            "onPageUpdate",
            `(page) => __comp__.props.onNotebookPageChange(${noteBookId}, page)`,
        );
        noteBook.setAttribute(
            "onWillActivatePage",
            `(page) => __comp__.onWillChangeNotebookPage?.(${noteBookId}, page)`,
        );
        noteBook.setAttribute(
            "isFieldInvalid",
            `(fieldName) => __comp__.props.record.isFieldInvalid(fieldName)`,
        );

        for (const child of el.children) {
            if (getTag(child, true) !== "page") {
                continue;
            }
            const invisible = getModifier(child, "invisible");
            if (
                !params.compileInvisibleNodes &&
                (invisible === "True" || invisible === "1")
            ) {
                continue;
            }

            const pageSlot = createElement("t");
            append(noteBook, pageSlot);

            const pageId = `page_${this.id++}`;
            const pageTitle = toStringExpression(
                child.getAttribute("string") || child.getAttribute("name") || "",
            );
            const pageNodeName = toStringExpression(child.getAttribute("name") || "");

            pageSlot.setAttribute("t-set-slot", pageId);
            pageSlot.setAttribute("title", pageTitle);
            pageSlot.setAttribute("name", pageNodeName);
            if (child.className) {
                pageSlot.setAttribute("className", toStringExpression(child.className));
            }

            if (child.getAttribute("autofocus") === "autofocus") {
                noteBook.setAttribute(
                    "defaultPage",
                    `__comp__.props.record.isNew ? "${pageId}" : (__comp__.props.activeNotebookPages[${noteBookId}] || "${pageId}")`,
                );
            }

            const isVisibleExpr = makeIsVisibleExpr(invisible);
            pageSlot.setAttribute("isVisible", isVisibleExpr);

            const pageFields = [];
            for (const contents of child.children) {
                append(
                    pageSlot,
                    this.compileNode(contents, {
                        ...params,
                        notebookPageFields: pageFields,
                        currentSlot: pageSlot,
                    }),
                );
            }
            pageSlot.setAttribute("fieldNames", `${JSON.stringify(pageFields)}`);
            params.notebookPageFields?.push(...pageFields);
        }

        return noteBook;
    }

    /**
     * @param {Element} el
     * @param {Record<string, any>} params
     * @returns {Element}
     */
    compileSetting(el, params) {
        const setting = createElement(params.componentName || "Setting", {
            info: toStringExpression(el.getAttribute("info") || ""),
            title: toStringExpression(el.getAttribute("title") || ""),
            help: toStringExpression(el.getAttribute("help") || ""),
            companyDependent: exprToBoolean(el.getAttribute("company_dependent") || "")
                ? "true"
                : "false",
            documentation: toStringExpression(el.getAttribute("documentation") || ""),
            record: `__comp__.props.record`,
        });
        if (el.getAttribute("id")) {
            setting.setAttribute("id", toStringExpression(el.getAttribute("id")));
        }
        let string = toStringExpression(el.getAttribute("string") || "");
        let addLabel = true;
        Array.from(el.children).forEach((child, index) => {
            if (getTag(child, true) === "field" && index === 0) {
                const fieldSlot = createElement("t", {
                    "t-set-slot": "fieldSlot",
                });
                const field = this.compileNode(/** @type {Element} */ (child), params);
                if (field) {
                    append(fieldSlot, field);
                    setting.setAttribute(
                        "fieldInfo",
                        /** @type {Element} */ (field).getAttribute("fieldInfo") ?? "",
                    );

                    addLabel = child.hasAttribute("nolabel")
                        ? child.getAttribute("nolabel") !== "1"
                        : true;
                    const fieldName = child.getAttribute("name");
                    string = child.hasAttribute("string")
                        ? toStringExpression(child.getAttribute("string"))
                        : string;
                    setting.setAttribute("fieldName", toStringExpression(fieldName));
                    setting.setAttribute(
                        "fieldId",
                        toStringExpression(child.getAttribute("field_id")),
                    );
                }
                append(setting, fieldSlot);
            } else {
                append(
                    setting,
                    this.compileNode(/** @type {Element} */ (child), params),
                );
            }
        });
        setting.setAttribute("string", string);
        setting.setAttribute("addLabel", String(addLabel));
        return setting;
    }

    /**
     * @param {Element} el
     * @returns {Element}
     */
    compileSeparator(el) {
        const separator = makeSeparator(el.getAttribute("string"));
        copyAttributes(el, separator);
        return separator;
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
            const compiled = this.compileNode(/** @type {Element} */ (child), params);
            if (!compiled) {
                continue;
            }
            if (compiled.nodeName === "ButtonBox") {
                continue;
            }
            if (getTag(child, true) === "field") {
                /** @type {Element} */ (compiled).setAttribute("showTooltip", "true");
            }
            append(sheetFG, compiled);
        }
        return sheetBG;
    }
}
