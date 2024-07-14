/* @odoo-module */

import { patchUiSize } from "@mail/../tests/helpers/patch_ui_size";
import { start } from "@mail/../tests/helpers/test_utils";

import { nextTick } from "@web/../tests/helpers/utils";
import { click, contains } from "@web/../tests/utils";

QUnit.module("softphone_mobile");

QUnit.test(
    "Clicking on the top bar does not fold the softphone window on small devices.",
    async () => {
        patchUiSize({ width: 360, height: 800 });
        start();
        await click(".o_menu_systray button[title='Open Softphone']");
        await click(".o-voip-Softphone-topbar");
        await nextTick();
        await contains(".o-voip-Softphone-content");
    }
);

QUnit.test(
    "The cursor when hovering over the top bar is not a pointer on small devices.",
    async (assert) => {
        patchUiSize({ width: 360, height: 800 });
        start();
        await click(".o_menu_systray button[title='Open Softphone']");
        await contains(".o-voip-Softphone");
        assert.strictEqual(getComputedStyle($(".o-voip-Softphone-topbar")[0]).cursor, "auto");
    }
);
