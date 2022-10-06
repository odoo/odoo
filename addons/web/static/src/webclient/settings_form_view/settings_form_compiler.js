/** @odoo-module **/

import { append, createElement } from "@web/core/utils/xml";
import { FormCompiler } from "@web/views/form/form_compiler";
import { getModifier } from "@web/views/view_compiler";

function compileSettingsPage(el, params) {
    const settingsPage = createElement("SettingsPage");
    settingsPage.setAttribute("slots", "{NoContentHelper:props.slots.NoContentHelper}");
    settingsPage.setAttribute("initialTab", "props.initialApp");
    settingsPage.setAttribute("t-slot-scope", "settings");

    //props
    const modules = [];

    for (const child of el.children) {
        if (child.nodeName === "div" && child.classList.value.includes("app_settings_block")) {
            params.module = {
                key: child.getAttribute("data-key"),
                string: child.getAttribute("string"),
                imgurl: getAppIconUrl(child.getAttribute("data-key")),
                isVisible: getModifier(child, "invisible"),
            };
            if (!child.classList.value.includes("o_not_app")) {
                modules.push(params.module);
                append(settingsPage, this.compileNode(child, params));
            }
        }
    }

    settingsPage.setAttribute("modules", JSON.stringify(modules));
    return settingsPage;
}

function getAppIconUrl(module) {
    return module === "general_settings"
        ? "/base/static/description/settings.png"
        : "/" + module + "/static/description/icon.png";
}

function compileSettingsApp(el, params) {
    const settingsApp = createElement("SettingsApp");
    settingsApp.setAttribute("t-props", JSON.stringify(params.module));
    settingsApp.setAttribute("selectedTab", "settings.selectedTab");

    for (const child of el.children) {
        append(settingsApp, this.compileNode(child, params));
    }

    return settingsApp;
}

function compileSettingsHeader(el, params) {
    const header = el.cloneNode();
    for (const child of el.children) {
        append(header, this.compileNode(child, { ...params, settingType: "header" }));
    }
    return header;
}

let settingsContainer = null;

function compileSettingsGroupTitle(el, params) {
    if (!settingsContainer) {
        settingsContainer = createElement("SettingsContainer");
    }

    settingsContainer.setAttribute("title", `\`${el.textContent}\``);
}

function compileSettingsGroupTip(el, params) {
    if (!settingsContainer) {
        settingsContainer = createElement("SettingsContainer");
    }

    settingsContainer.setAttribute("tip", `\`${el.textContent}\``);
}

function compileSettingsContainer(el, params) {
    if (!settingsContainer) {
        settingsContainer = createElement("SettingsContainer");
    }

    for (const child of el.children) {
        append(settingsContainer, this.compileNode(child, params));
    }
    const res = settingsContainer;
    settingsContainer = null;
    return res;
}

function compileSettingBox(el, params) {
    const setting = createElement("Setting");
    params.labels = [];

    if (params.settingType) {
        setting.setAttribute("type", `\`${params.settingType}\``);
    }
    if (el.getAttribute("title")) {
        setting.setAttribute("title", `\`${el.getAttribute("title")}\``);
    }
    for (const child of el.children) {
        append(setting, this.compileNode(child, params));
    }
    setting.setAttribute("labels", JSON.stringify(params.labels));
    return setting;
}

function compileField(el, params) {
    const res = this.compileField(el, params);
    let widgetName;
    if (el.hasAttribute("widget")) {
        widgetName = el.getAttribute("widget");
        const label = params.getFieldExpr(el.getAttribute("name"), widgetName);
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

function compileForm() {
    const res = this.compileForm(...arguments);
    res.classList.remove("o_form_nosheet");
    res.classList.remove("p-2");
    res.classList.remove("px-lg-5");
    return res;
}

export class SettingsFormCompiler extends FormCompiler {
    setup() {
        super.setup();
        this.compilers.unshift(
            { selector: "form", fn: compileForm },
            { selector: "div.settings", fn: compileSettingsPage },
            { selector: "div.app_settings_block", fn: compileSettingsApp },
            { selector: "div.app_settings_header", fn: compileSettingsHeader },
            // objects to show/hide in the search
            { selector: "div.o_setting_box", fn: compileSettingBox },
            { selector: "div.o_settings_container", fn: compileSettingsContainer },
            // h2
            { selector: "h2", fn: compileSettingsGroupTitle },
            { selector: "h3.o_setting_tip", fn: compileSettingsGroupTip },
            // search terms and highlight :
            { selector: "label", fn: compileLabel },
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
