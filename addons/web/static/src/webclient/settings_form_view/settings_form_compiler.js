/** @odoo-module **/

import { createElement } from "@web/core/utils/xml";
import { FormCompiler } from "@web/views/form/form_compiler";
import { append } from "@web/views/helpers/view_compiler";

function compileSettingsPage(el, params) {
    const settings = createElement("SettingsPage");
    settings.setAttribute("t-slot-scope", "settings");

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
            params.config = {};
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

    params.config.app = el.getAttribute("data-key");
    params.config.groupName = undefined;
    params.config.groupTitle = undefined;
    params.config.container = undefined;
    params.config.settingBox = undefined;

    for (const child of el.children) {
        append(settingsBlock, this.compileNode(child, params));
    }

    settingsBlock.setAttribute(
        "t-if",
        `!searchValue.value or search("app", "${el.getAttribute("data-key")}")`
    );

    return settingsBlock;
}

let groupTitleId = 0;

function compileSettingsGroupTitle(el, params) {
    groupTitleId++;
    const res = this.compileGenericNode(el, params);
    const groupName = res.textContent;

    params.config.groupTitle = groupTitleId;
    params.config.groupName = groupName;
    params.config.container = undefined;
    params.config.settingBox = undefined;
    //HighlightText
    const highlight = createElement("HighlightText");
    highlight.setAttribute("originalText", `\`${groupName}\``);
    append(res, highlight);
    res.firstChild.remove();

    params.labels.push({
        label: groupName.trim(),
        ...params.config,
    });

    res.setAttribute("t-if", `!searchValue.value or search("groupTitle", ${groupTitleId})`);
    return res;
}

let containerId = 0;

function compileSettingsContainer(el, params) {
    containerId++;
    params.config.container = containerId;
    params.config.settingBox = undefined;
    params.containerLabels = [];
    const res = this.compileGenericNode(el, params);
    res.setAttribute("t-if", `!searchValue.value or search("container", ${containerId})`);
    return res;
}

let settingBoxId = 0;

function compileSettingBox(el, params) {
    settingBoxId++;
    params.config.settingBox = settingBoxId;
    const res = this.compileGenericNode(el, params);
    res.setAttribute("t-if", `!searchValue.value or search("settingBox", ${settingBoxId})`);
    return res;
}

function compileField(el, params) {
    const res = this.compileField(el, params);
    let widgetName;
    if (el.hasAttribute("widget")) {
        widgetName = el.getAttribute("widget");
    }
    if (params.getFieldExpr) {
        const label = params.getFieldExpr(el.getAttribute("name"), widgetName);
        if (label) {
            params.labels.push({
                label,
                ...params.config,
            });
        }
    }
    return res;
}

function compileLabel(el, params) {
    const res = this.compileLabel(el, params);
    if (res.textContent && res.tagName !== "FormLabel") {
        params.labels.push({
            label: res.textContent.trim(),
            ...params.config,
        });
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
        params.labels.push({
            label: res.textContent.trim(),
            ...params.config,
        });
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
            },
            // widget are not supported for the moment
            {
                tag: "widget",
                fn: () => {},
            }
        );
    }
    createLabelFromField(fieldId, fieldName, fieldString, label, params) {
        const res = super.createLabelFromField(fieldId, fieldName, fieldString, label, params);
        let labelText = label.textContent || fieldString;
        labelText = labelText ? labelText : params.record.fields[fieldName].string;

        params.labels.push({
            label: labelText,
            ...params.config,
        });
        return res;
    }
}
