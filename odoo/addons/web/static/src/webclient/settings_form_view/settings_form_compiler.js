/** @odoo-module **/

import { append, createElement } from "@web/core/utils/xml";
import { FormCompiler } from "@web/views/form/form_compiler";
import { toStringExpression } from "@web/views/utils";
import { isTextNode } from "@web/views/view_compiler";

export class SettingsFormCompiler extends FormCompiler {
    setup() {
        super.setup();
        this.compilers.push(
            { selector: "app", fn: this.compileApp },
            { selector: "block", fn: this.compileBlock }
        );
    }

    compileForm(el, params) {
        const settingsPage = createElement("SettingsPage");
        settingsPage.setAttribute(
            "slots",
            "{NoContentHelper:__comp__.props.slots.NoContentHelper}"
        );
        settingsPage.setAttribute("initialTab", "__comp__.props.initialApp");
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
        params.componentName =
            el.getAttribute("type") === "header" ? "SettingHeader" : "SearchableSetting";
        const res = super.compileSetting(el, params);
        return res;
    }

    compileNode(node, params, evalInvisible) {
        if (isTextNode(node)) {
            if (node.textContent.trim()) {
                return createElement("HighlightText", {
                    originalText: toStringExpression(node.textContent),
                });
            }
        }
        return super.compileNode(node, params, evalInvisible);
    }

    compileButton(el, params) {
        const res = super.compileButton(el, params);
        if (res.hasAttribute("string") && res.children.length === 0) {
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
