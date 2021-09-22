/** @odoo-module */
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

import dialogs from "web.view_dialogs";
import { ComponentAdapter } from "web.OwlCompatibility";

function runJSTestsItem({ env }) {
    const runTestsURL = browser.location.origin + "/web/tests?mod=*";
    return {
        type: "item",
        description: env._t("Run JS Tests"),
        href: runTestsURL,
        callback: () => {
            browser.open(runTestsURL);
        },
        sequence: 10,
    };
}

function runJSTestsMobileItem({ env }) {
    const runTestsMobileURL = browser.location.origin + "/web/tests/mobile?mod=*";
    return {
        type: "item",
        description: env._t("Run JS Mobile Tests"),
        href: runTestsMobileURL,
        callback: () => {
            browser.open(runTestsMobileURL);
        },
        sequence: 20,
    };
}

export function openViewItem({ env }) {
    async function onSelected(records) {
        const views = await env.services.orm.searchRead(
            "ir.ui.view",
            [["id", "=", records[0].id]],
            ["name", "model", "type"],
            { limit: 1 }
        );
        const view = views[0];
        view.type = view.type === "tree" ? "list" : view.type; // ignore tree view
        env.services.action.doAction({
            type: "ir.actions.act_window",
            name: view.name,
            res_model: view.model,
            views: [[view.id, view.type]],
        });
    }

    return {
        type: "item",
        description: env._t("Open View"),
        callback: () => {
            const adapterParent = new ComponentAdapter(null, { Component: owl.Component });
            const selectCreateDialog = new dialogs.SelectCreateDialog(adapterParent, {
                res_model: "ir.ui.view",
                title: env._t("Select a view"),
                disable_multiple_selection: true,
                domain: [
                    ["type", "!=", "qweb"],
                    ["type", "!=", "search"],
                ],
                on_selected: onSelected,
            });

            selectCreateDialog.open();
        },
        sequence: 40,
    };
}

// This separates the items defined above from global items that aren't webclient-only
function globalSeparator() {
    return {
        type: "separator",
        sequence: 400,
    };
}

registry
    .category("debug")
    .category("default")
    .add("runJSTestsItem", runJSTestsItem)
    .add("runJSTestsMobileItem", runJSTestsMobileItem)
    .add("globalSeparator", globalSeparator)
    .add("openViewItem", openViewItem);
