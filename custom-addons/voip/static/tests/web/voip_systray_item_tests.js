/* @odoo-module */

import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains } from "@web/../tests/utils";

QUnit.module("voip_systray_item");

QUnit.test("Clicking on systray item when softphone is hidden shows the softphone.", async () => {
    start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await contains(".o-voip-Softphone");
});

QUnit.test(
    "Clicking on systray item when softphone is displayed and unfolded hides the softphone.",
    async () => {
        start();
        await click(".o_menu_systray button[title='Open Softphone']");
        await click(".o_menu_systray button[title='Close Softphone']");
        await contains(".o-voip-Softphone");
    }
);

QUnit.test(
    "Clicking on systray item when softphone is displayed but folded unfolds the softphone.",
    async () => {
        start();
        await click(".o_menu_systray button[title='Open Softphone']");
        await click(".o-voip-Softphone-topbar"); // fold
        await click(".o_menu_systray button[title='Unfold Softphone']");
        await contains(".o-voip-Softphone-content");
    }
);
