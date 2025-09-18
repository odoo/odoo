// @ts-check

/** @module @web/webclient/debug/debug_items - Debug menu items for running unit tests, opening views, and toggling technical data */

import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";

/**
 * Debug menu item: open the unit test runner.
 * @returns {Object} debug menu item descriptor
 */
function runUnitTestsItem() {
    const href = "/web/tests?debug=assets";
    return {
        type: "item",
        description: _t("Run Unit Tests"),
        href,
        callback: () => browser.open(href),
        sequence: 450,
        section: "testing",
    };
}

/**
 * Debug menu item: open any view by selecting it from a dialog.
 * @param {{ env: Object }} params
 * @returns {Object} debug menu item descriptor
 */
export function openViewItem({ env }) {
    async function onSelected(records) {
        const views = await env.services.orm.searchRead(
            "ir.ui.view",
            [["id", "=", records[0]]],
            ["name", "model", "type"],
            { limit: 1 },
        );
        const view = views[0];
        env.services.action.doAction({
            type: "ir.actions.act_window",
            name: view.name,
            res_model: view.model,
            views: [[view.id, view.type]],
        });
    }

    return {
        type: "item",
        description: _t("Open View"),
        callback: () => {
            env.services.dialog.add(SelectCreateDialog, {
                resModel: "ir.ui.view",
                title: _t("Select a view"),
                multiSelect: false,
                domain: [
                    ["type", "!=", "qweb"],
                    ["type", "!=", "search"],
                ],
                onSelected,
            });
        },
        sequence: 540,
        section: "tools",
    };
}

registry
    .category("debug")
    .category("default")
    .add("runUnitTestsItem", /** @type {any} */ (runUnitTestsItem))
    .add("openViewItem", /** @type {any} */ (openViewItem));
