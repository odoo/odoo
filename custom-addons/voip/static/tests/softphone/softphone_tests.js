/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { translatedTerms } from "@web/core/l10n/translation";
import { patchWithCleanup, triggerHotkey } from "@web/../tests/helpers/utils";
import { click, contains, insertText } from "@web/../tests/utils";

/**
 * @param {number} numberOfMissedCalls
 * @returns {function}
 */
const mockMissedCalls = (numberOfMissedCalls) =>
    async function (route, _args, originalRpc) {
        if (route === "/mail/init_messaging") {
            const res = await originalRpc(...arguments);
            res.voipConfig.missedCalls = numberOfMissedCalls;
            return res;
        }
    };

QUnit.module("softphone");

QUnit.test("Clicking on top bar when softphone is unfolded folds the softphone.", async () => {
    start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await contains(".o-voip-Softphone-content");
    await click(".o-voip-Softphone-topbar");
    await contains(".o-voip-Softphone-content", { count: 0 });
});

QUnit.test("Clicking on top bar when softphone is folded unfolds the softphone.", async () => {
    start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click(".o-voip-Softphone-topbar"); // fold
    await click(".o-voip-Softphone-topbar");
    await contains(".o-voip-Softphone-content");
});

QUnit.test("Clicking on close button closes the softphone.", async () => {
    start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await contains(".o-voip-Softphone");
    await click(".o-voip-Softphone button[title='Close']");
    await contains(".o-voip-Softphone", { count: 0 });
});

QUnit.test("Search bar is focused after opening the softphone.", async () => {
    start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await contains("input[placeholder='Search']:focus");
});

QUnit.test("Search bar is focused after unfolding the softphone.", async () => {
    start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click(".o-voip-Softphone-topbar"); // fold
    await click(".o-voip-Softphone-topbar"); // unfold
    await contains("input[placeholder='Search']:focus");
});

QUnit.test("“Next activities” is the active tab by default.", async () => {
    start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await contains(".nav-link.active", { text: "Next Activities" });
});

QUnit.test("Clicking on a tab makes it the active tab.", async () => {
    start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click(".nav-link", { text: "Contacts" });
    await contains(".nav-link.active", { text: "Contacts" });
    await contains(".nav-link.active");
});

QUnit.test("Click on the “Numpad button” to open and close the numpad.", async () => {
    start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click("button[title='Open Numpad']");
    await contains(".o-voip-Numpad");
    await click("button[title='Close Numpad']");
    await contains(".o-voip-Numpad", { count: 0 });
});

QUnit.test(
    "The softphone top bar text is “VoIP” as long as there is no missed calls.",
    async () => {
        start({ mockRPC: mockMissedCalls(0) });
        await click(".o_menu_systray button[title='Open Softphone']");
        await contains(".o-voip-Softphone-topbar", { text: "VoIP" });
    }
);

QUnit.test(
    "The softphone automatically opens folded when there is at least 1 missed call.",
    async () => {
        start({ mockRPC: mockMissedCalls(1) });
        await contains(".o-voip-Softphone"); // it's displayed…
        await contains(".o-voip-Softphone-content", { count: 0 }); // but it's folded
    }
);

QUnit.test(
    "The softphone top bar text is “1 missed call” when there is 1 missed call.",
    async () => {
        start({ mockRPC: mockMissedCalls(1) });
        await contains(".o-voip-Softphone-topbar", { text: "1 missed call" });
    }
);

QUnit.test(
    "The softphone top bar text allows a specific translation for the dual grammatical number.",
    async () => {
        patchWithCleanup(translatedTerms, { "2 missed calls": "2 مكالمة فائتة" });
        start({ mockRPC: mockMissedCalls(2) });
        await contains(".o-voip-Softphone-topbar", { text: "2 مكالمة فائتة" });
    }
);

QUnit.test(
    "The softphone top bar text is “513 missed calls” when there is 513 missed calls",
    async () => {
        start({ mockRPC: mockMissedCalls(513) });
        await contains(".o-voip-Softphone-topbar", { text: "513 missed calls" });
    }
);

QUnit.test("The cursor when hovering over the top bar has “pointer” style", async (assert) => {
    start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await contains(".o-voip-Softphone-topbar");
    assert.strictEqual(getComputedStyle($(".o-voip-Softphone-topbar")[0]).cursor, "pointer");
});

QUnit.test(
    "When a call is created, a partner with a corresponding phone number is displayed",
    async () => {
        const pyEnv = await startServer();
        const phoneNumber = "0456 703 6196";
        pyEnv["res.partner"].create({ name: "Maxime Randonnées", mobile: phoneNumber });
        const { advanceTime } = await start({ hasTimeControl: true });
        await click(".o_menu_systray button[title='Open Softphone']");
        await click("button[title='Open Numpad']");
        await insertText("input[placeholder='Enter the number…']", phoneNumber);
        await triggerHotkey("Enter");
        await advanceTime(5000);
        await contains(".o-voip-CorrespondenceDetails", { text: "Maxime Randonnées" });
    }
);
