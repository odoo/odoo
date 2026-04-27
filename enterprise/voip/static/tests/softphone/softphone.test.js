import { describe, expect, test } from "@odoo/hoot";
import { advanceTime } from "@odoo/hoot-mock";
import {
    click,
    contains,
    insertText,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { setupVoipTests } from "@voip/../tests/voip_test_helpers";
import { translatedTerms } from "@web/core/l10n/translation";
import { patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
setupVoipTests();

test("Clicking on top bar when softphone is unfolded folds the softphone.", async () => {
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await contains(".o-voip-Softphone-content");
    await click(".o-voip-Softphone-topbar");
    await contains(".o-voip-Softphone-content", { count: 0 });
});

test("Clicking on top bar when softphone is folded unfolds the softphone.", async () => {
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click(".o-voip-Softphone-topbar"); // fold
    await click(".o-voip-Softphone-topbar");
    await contains(".o-voip-Softphone-content");
});

test("Clicking on close button closes the softphone.", async () => {
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await contains(".o-voip-Softphone");
    await click(".o-voip-Softphone button[title='Close']");
    await contains(".o-voip-Softphone", { count: 0 });
});

test("Search bar is focused after opening the softphone.", async () => {
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await contains("input[placeholder='Search']:focus");
});

test("Search bar is focused after unfolding the softphone.", async () => {
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click(".o-voip-Softphone-topbar"); // fold
    await click(".o-voip-Softphone-topbar"); // unfold
    await contains("input[placeholder='Search']:focus");
});

test("“Next activities” is the active tab by default.", async () => {
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await contains(".nav-link.active", { text: "Next Activities" });
});

test("Clicking on a tab makes it the active tab.", async () => {
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click(".nav-link", { text: "Contacts" });
    await contains(".nav-link.active", { text: "Contacts" });
    await contains(".nav-link.active");
});

test("Click on the “Numpad button” to open and close the numpad.", async () => {
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click("button[title='Open Numpad']");
    await contains(".o-voip-Numpad");
    await click("button[title='Close Numpad']");
    await contains(".o-voip-Numpad", { count: 0 });
});

test("The softphone top bar text is “VoIP” as long as there is no missed calls.", async () => {
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await contains(".o-voip-Softphone-topbar", { text: "VoIP" });
});

test("The softphone automatically opens folded when there is at least 1 missed call.", async () => {
    const pyEnv = await startServer();
    pyEnv["voip.call"].create({ state: "missed", user_id: serverState.userId });
    await start();
    await contains(".o-voip-Softphone"); // it's displayed…
    await contains(".o-voip-Softphone-content", { count: 0 }); // but it's folded
});

test("The softphone top bar text is “1 missed call” when there is 1 missed call.", async () => {
    const pyEnv = await startServer();
    pyEnv["voip.call"].create({ state: "missed", user_id: serverState.userId });
    await start();
    await contains(".o-voip-Softphone-topbar", { text: "1 missed call" });
});

test("The softphone top bar text allows a specific translation for the dual grammatical number.", async () => {
    const pyEnv = await startServer();
    patchWithCleanup(translatedTerms, { "2 missed calls": "2 مكالمة فائتة" });
    pyEnv["voip.call"].create({ state: "missed", user_id: serverState.userId });
    pyEnv["voip.call"].create({ state: "missed", user_id: serverState.userId });
    await start();
    await contains(".o-voip-Softphone-topbar", { text: "2 مكالمة فائتة" });
});

test("The softphone top bar text is “513 missed calls” when there is 513 missed calls", async () => {
    const pyEnv = await startServer();
    for (let i = 0; i < 513; i++) {
        pyEnv["voip.call"].create({ state: "missed", user_id: serverState.userId });
    }
    await start();
    await contains(".o-voip-Softphone-topbar", { text: "513 missed calls" });
});

test("The cursor when hovering over the top bar has “pointer” style", async () => {
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await contains(".o-voip-Softphone-topbar");
    expect(".o-voip-Softphone-topbar:first").toHaveStyle({ cursor: "pointer" });
});

test("Using VoIP in prod mode without configuring the server shows an error", async () => {
    const pyEnv = await startServer();
    const providerId = pyEnv["voip.provider"].create({
        mode: "prod",
        name: "Axivox super cool",
        pbx_ip: "",
        ws_server: "",
    });
    pyEnv["res.users"].write([serverState.userId], { voip_provider_id: providerId });
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await contains(".o-voip-Softphone-error");
});

test("When a call is created, a partner with a corresponding phone number is displayed", async () => {
    const pyEnv = await startServer();
    const phoneNumber = "0456 703 6196";
    pyEnv["res.partner"].create({ name: "Maxime Randonnées", mobile: phoneNumber });
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click("button[title='Open Numpad']");
    await insertText("input[placeholder='Enter the number…']", phoneNumber);
    await triggerHotkey("Enter");
    await advanceTime(5000);
    await contains(".o-voip-CorrespondenceDetails", { text: "Maxime Randonnées" });
});
