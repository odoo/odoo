/** @odoo-module **/

import { append, createElement, getTag } from "@web/core/utils/xml";
import { FormCompiler } from "@web/views/form/form_compiler";
import { toStringExpression } from "@web/views/utils";

function compileApp(el, params) {
    if (el.getAttribute("notApp") === "1") {
        return;
    }
    const module = {
        key: el.getAttribute("name"),
        string: el.getAttribute("string"),
        imgurl:
            el.getAttribute("logo") ||
            "/" + el.getAttribute("name") + "/static/description/icon.png",
    };
    params.modules.push(module);
    const settingsApp = createElement("SettingsApp", {
        key: toStringExpression(module.key),
        string: toStringExpression(module.string || ""),
        imgurl: toStringExpression(module.imgurl),
        selectedTab: "settings.selectedTab",
    });

    for (const child of el.children) {
        append(settingsApp, this.compileNode(child, params));
    }

    return settingsApp;
}

function compileBlock(el, params) {
    const settingsContainer = createElement("SettingsBlock", {
        title: toStringExpression(el.getAttribute("title") || ""),
        tip: toStringExpression(el.getAttribute("help") || ""),
    });
    for (const child of el.children) {
        append(settingsContainer, this.compileNode(child, params));
    }
    return settingsContainer;
}

function compileSetting(el, params) {
    const componentName = el.getAttribute("type") === "header" ? "SettingHeader" : "Setting";
    const setting = createElement(componentName, {
        title: toStringExpression(el.getAttribute("title") || ""),
        help: toStringExpression(el.getAttribute("help") || ""),
        companyDependent: el.getAttribute("company_dependent") === "1" || "false",
        documentation: toStringExpression(el.getAttribute("documentation") || ""),
        record: `this.props.record`,
    });
    let string = toStringExpression(el.getAttribute("string") || "");
    let addLabel = true;
    params.labels = [];
    Array.from(el.children).forEach((child, index) => {
        if (getTag(child, true) === "field" && index === 0) {
            const fieldSlot = createElement("t", { "t-set-slot": "fieldSlot" });
            const field = this.compileNode(child, params);
            if (field) {
                append(fieldSlot, field);
                setting.setAttribute("fieldInfo", field.getAttribute("fieldInfo"));

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
                    toStringExpression(child.getAttribute("field_id") || fieldName)
                );
            }
            append(setting, fieldSlot);
        } else {
            append(setting, this.compileNode(child, params));
        }
    });
    setting.setAttribute("string", string);
    setting.setAttribute("addLabel", addLabel);
    setting.setAttribute("labels", JSON.stringify(params.labels));
    return setting;
}

function compileField(el, params) {
    const res = this.compileField(el, params);
    if (el.hasAttribute("widget")) {
        const label = params.getFieldExpr(el.getAttribute("name"), el.getAttribute("widget"));
        if (label) {
            params.labels.push(label);
        }
    }
    return res;
}

const labelsWeak = new WeakMap();
function compileLabel(el, params) {
    const res = this.compileLabel(el, params);
    // It the node is a FormLabel component node, the label is
    // localized *after* the field.
    // We don't know yet if the label refers to a field or not.
    if (res.textContent && res.tagName !== "FormLabel") {
        params.labels.push(res.textContent.trim());
        labelsWeak.set(res, { textContent: res.textContent });
        highlightElement(res);
    }
    return res;
}

function compileGenericLabel(el, params) {
    const res = this.compileGenericNode(el, params);
    if (res.textContent) {
        params.labels.push(res.textContent.trim());
        highlightElement(res);
    }
    return res;
}

function highlightElement(el) {
    for (const child of el.childNodes) {
        if (child.nodeType === Node.TEXT_NODE) {
            if (child.textContent.trim()) {
                const highlight = createElement("HighlightText");
                highlight.setAttribute("originalText", `\`${child.textContent}\``);
                el.replaceChild(highlight, child);
            }
        } else if (child.childNodes.length) {
            highlightElement(child);
        }
    }
}

function compileForm(el, params) {
    const settingsPage = createElement("SettingsPage");
    settingsPage.setAttribute("slots", "{NoContentHelper:this.props.slots.NoContentHelper}");
    settingsPage.setAttribute("initialTab", "this.props.initialApp");
    settingsPage.setAttribute("t-slot-scope", "settings");

    //props
    params.modules = [];

    const res = this.compileForm(...arguments);
    res.classList.remove("o_form_nosheet");

    settingsPage.setAttribute("modules", JSON.stringify(params.modules));

    for (const child of res.childNodes) {
        append(settingsPage, this.compileNode(child, params));
    }
    while (res.lastChild) {
        res.removeChild(res.lastChild);
    }
    append(res, settingsPage);

    return res;
}

export class SettingsFormCompiler extends FormCompiler {
    setup() {
        super.setup();
        this.compilers.unshift(
            { selector: "form", fn: compileForm },
            { selector: "app", fn: compileApp },
            { selector: "block", fn: compileBlock },
            { selector: "setting", fn: compileSetting },
            // search terms and highlight :
            { selector: "label", fn: compileLabel, doNotCopyAttributes: true },
            { selector: "span.o_form_label", fn: compileGenericLabel },
            { selector: "div.text-muted", fn: compileGenericLabel },
            { selector: "field", fn: compileField }
        );
    }
    createLabelFromField(fieldId, fieldName, fieldString, label, params) {
        const labelweak = labelsWeak.get(label);
        if (labelweak) {
            // Undo what we've done when we where not sure whether this label was attached to a field
            // Now, we now it is.
            label.textContent = labelweak.textContent;
        }
        const res = super.createLabelFromField(fieldId, fieldName, fieldString, label, params);
        if (labelweak || label.hasAttribute("data-no-label")) {
            // the work of pushing the label in the search structure is already done
            return res;
        }
        let labelText = label.textContent || fieldString;
        labelText = labelText ? labelText : params.record.fields[fieldName].string;

        params.labels.push(labelText);
        return res;
    }
}
