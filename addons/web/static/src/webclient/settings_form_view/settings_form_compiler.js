/** @odoo-module **/

import { append, createElement, getTag } from "@web/core/utils/xml";
import { FormCompiler } from "@web/views/form/form_compiler";
import { toStringExpression } from "@web/views/utils";
import { isTextNode } from "@web/views/view_compiler";

export class SettingsFormCompiler extends FormCompiler {
    setup() {
        super.setup();
        this.compilers.push(
            { selector: "app", fn: this.compileApp },
            { selector: "block", fn: this.compileBlock },
            { selector: "setting", fn: this.compileSetting }
        );
    }

    compileForm(el, params) {
        const settingsPage = createElement("SettingsPage");
        settingsPage.setAttribute("slots", "{NoContentHelper:this.props.slots.NoContentHelper}");
        settingsPage.setAttribute("initialTab", "this.props.initialApp");
        settingsPage.setAttribute("t-slot-scope", "settings");

        //props
        params.modules = [];

        const res = super.compileForm(...arguments);
        res.classList.remove("o_form_nosheet");

        settingsPage.setAttribute("modules", JSON.stringify(params.modules));

        // Move the compiled content of the form inside the settingsPage
        while (res.firstChild) {
            append(settingsPage, res.firstChild);
        }
        append(res, settingsPage);

        return res;
    }

    compileApp(el, params) {
        if (el.getAttribute("notApp") === "1") {
            //An app noted with notApp="1" is not rendered.

            //This hack is used when a technical module defines settings, and we don't want to render
            //the settings until the corresponding app is not installed.

            // For example, when installing the module website_sale, the module sale is also installed,
            // but we don't want to render its settings (notApp="1").
            // On the contrary, when sale_management is installed, the module sale is also installed
            // but in this case we want to see its settings (notApp="0").
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

    compileBlock(el, params) {
        const settingsContainer = createElement("SettingsBlock", {
            title: toStringExpression(el.getAttribute("title") || ""),
            tip: toStringExpression(el.getAttribute("help") || ""),
        });
        for (const child of el.children) {
            append(settingsContainer, this.compileNode(child, params));
        }
        return settingsContainer;
    }

    compileSetting(el, params) {
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
        delete params.labels;
        return setting;
    }

    compileField(el, params) {
        const res = super.compileField(el, params);
        if (params.labels && el.hasAttribute("widget")) {
            const label = params.getFieldExpr(el.getAttribute("name"), el.getAttribute("widget"));
            if (label) {
                params.labels.push(label);
            }
        }
        return res;
    }

    compileNode(node, params, evalInvisible) {
        if (isTextNode(node)) {
            if (params.labels && node.textContent.trim()) {
                params.labels.push(node.textContent.trim());
                return createElement("HighlightText", {
                    originalText: toStringExpression(node.textContent),
                });
            }
        }
        return super.compileNode(node, params, evalInvisible);
    }

    createLabelFromField(fieldId, fieldName, fieldString, label, params) {
        const res = super.createLabelFromField(fieldId, fieldName, fieldString, label, params);
        if (res.hasAttribute("string") && params.labels) {
            params.labels.push(res.getAttribute("string"));
        }
        return res;
    }

    compileButton(el, params) {
        const res = super.compileButton(el, params);
        if (res.hasAttribute("string") && params.labels && res.children.length === 0) {
            params.labels.push(res.getAttribute("string"));
            const contentSlot = createElement("t");
            contentSlot.setAttribute("t-set-slot", "contents");
            const content = createElement("HighlightText", {
                originalText: res.getAttribute("string"),
            });
            append(contentSlot, content);
            append(res, contentSlot);
        }
        return res;
    }
}
