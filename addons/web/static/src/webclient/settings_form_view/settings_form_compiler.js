/** @odoo-module **/

import { createElement } from "@web/core/utils/xml";
import { FormCompiler } from "@web/views/form/form_compiler";
import { append } from "@web/views/helpers/view_compiler";

function compileSettingsPage(el, params) {
    const settings = createElement("SettingsPage");
    settings.setAttribute("t-slot-scope", "settings");

    //TODO: check if we cannot use a "registry" to make the if one the upper componenets (including the noContent)

    //props
    const modules = [];

    for (const child of el.children) {
        if (child.nodeName === "div" && child.classList.value.includes("app_settings_block")) {
            const module = {
                key: child.getAttribute("data-key"),
                string: child.getAttribute("string"),
                imgurl: getAppIconUrl(child.getAttribute("data-key")),
                notApp: child.classList.value.includes("o_not_app"),
            };
            params.module = module;
            if (!child.classList.value.includes("o_not_app")) {
                modules.push(module);
                append(settings, this.compileNode(child, params));
            }
        }
    }

    settings.setAttribute("modules", JSON.stringify(modules));
    return settings;
}

function getAppIconUrl(module) {
    return module === "general_settings"
        ? "/base/static/description/settings.png"
        : "/" + module + "/static/description/icon.png";
}

function compileSettingsApp(el, params) {
    const settingsBlock = createElement("SettingsApp");
    settingsBlock.setAttribute("t-props", JSON.stringify(params.module));
    settingsBlock.setAttribute("selectedTab", "settings.selectedTab");

    params.appLabels = [];
    params.group = {};
    for (const child of el.children) {
        append(settingsBlock, this.compileNode(child, params));
    }

    if (params.appLabels) {
        const labelExpr = `[${params.appLabels.join(",")}]`;
        settingsBlock.setAttribute("t-if", `!searchValue or search(${labelExpr})`);
    }

    return settingsBlock;
}

function compileSettingsGroupTitle(el, params) {
    const res = this.compileGenericNode(el, params);
    //HighlightText
    const highlight = createElement("HighlightText");
    const groupName = res.textContent;
    highlight.setAttribute("originalText", `\`${groupName}\``);
    append(res, highlight);
    res.firstChild.remove();
    params.appLabels.push(`\`${groupName.trim()}\``);
    res.setAttribute("t-if", `!searchValue or search([\`${groupName.trim()}\`])`);
    params.group = { name: groupName, el: res };
    return res;
}

function compileSettingsContainer(el, params) {
    params.containerLabels = [];
    const res = this.compileGenericNode(el, params);
    if (params.containerLabels) {
        if (params.group.name) {
            params.containerLabels.push(`"${params.group.name}"`);
        }
        const labelExpr = `[${params.containerLabels.join(",")}]`;
        res.setAttribute("t-if", `!searchValue or search(${labelExpr})`);
    }
    return res;
}

function compileSettingBox(el, params) {
    params.labels = [];
    const res = this.compileGenericNode(el, params);
    if (params.labels) {
        if (params.containerLabels) {
            params.containerLabels.push(params.labels);
        }
        params.appLabels.push(params.labels);
        if (params.group.name) {
            params.labels.push(`"${params.group.name}"`); // search in h2
            //Here
            const attr = params.group.el.getAttribute("t-if");
            const groupLabelsStrings = attr.substring(attr.indexOf("[") + 1, attr.lastIndexOf("]"));
            const groupLabels = groupLabelsStrings.split(",");
            groupLabels.push(params.labels);
            params.group.el.removeAttribute("t-if");
            const labelExpr = `[${groupLabels.join(",")}]`;
            params.group.el.setAttribute("t-if", `!searchValue or search(${labelExpr})`);
        }
        const labelExpr = `[${params.labels.join(",")}]`;
        res.setAttribute("t-if", `!searchValue or search(${labelExpr})`);
    }
    return res;
}

function compileField(el, params) {
    let widgetName;
    if (el.hasAttribute("widget")) {
        widgetName = el.getAttribute("widget");
    }
    if (params.labels) {
        params.labels.push(`getFieldExpr("${el.getAttribute("name")}", "${widgetName}")`);
    }
    return this.compileField(el, params);
}

function compileLabel(el, params) {
    const res = this.compileLabel(el, params);
    if (res.textContent && res.tagName !== "FormLabel") {
        if (params.labels) {
            params.labels.push(`\`${res.textContent.trim()}\``);
        }
        //HighlightText
        const highlight = createElement("HighlightText");
        highlight.setAttribute("originalText", `\`${res.textContent}\``);
        append(res, highlight);
        res.firstChild.remove();
    }
    return res;
}

function compileGenericLabel(el, params) {
    const res = this.compileGenericNode(el, params);
    if (res.textContent) {
        if (params.labels) {
            params.labels.push(`\`${res.textContent.trim()}\``);
        }
        //HighlightText
        const highlight = createElement("HighlightText");
        highlight.setAttribute("originalText", `\`${res.textContent}\``);
        append(res, highlight);
        res.firstChild.remove();
    }
    return res;
}

export class SettingsFormCompiler extends FormCompiler {
    setup() {
        super.setup();
        this.compilers.push(
            {
                tag: "div",
                class: "settings",
                fn: compileSettingsPage,
            },
            {
                tag: "div",
                class: "app_settings_block",
                fn: compileSettingsApp,
            },
            // objects to show/hide in the search
            {
                tag: "div",
                class: "o_setting_box",
                fn: compileSettingBox,
            },
            {
                tag: "div",
                class: "o_settings_container",
                fn: compileSettingsContainer,
            },
            // h2
            {
                tag: "h2",
                fn: compileSettingsGroupTitle,
            },
            // search terms and highlight :
            {
                tag: "label",
                fn: compileLabel,
            },
            {
                tag: "span",
                class: "o_form_label",
                fn: compileGenericLabel,
            },
            {
                tag: "div",
                class: "text-muted",
                fn: compileGenericLabel,
            },
            {
                tag: "field",
                fn: compileField,
            }
        );
    }
    //JPP: pas fan de ceci ....
    createLabelFromField(fieldId, fieldName, fieldString, label, params) {
        const res = super.createLabelFromField(fieldId, fieldName, fieldString, label, params);
        params.labels.push(res.getAttribute("string"));
        return res;
    }
}
