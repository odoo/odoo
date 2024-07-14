/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { browser } from "@web/core/browser/browser";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { click, contains } from "@web/../tests/utils";

QUnit.module("device_selection_dialog_mobile");

QUnit.test("Switch audio input", async () => {
    patchWithCleanup(browser, {
        navigator: {
            ...browser.navigator,
            userAgent: "Chrome/0.0.0 (Linux; Android 13; Odoo TestSuite)",
            mediaDevices: {
                async enumerateDevices() {
                    return [
                        {
                            deviceId: "default",
                            kind: "audioinput",
                        },
                        {
                            deviceId: "headset-earpiece-audio-input",
                            kind: "audioinput",
                        },
                        {
                            deviceId: "default-video-input",
                            kind: "videoinput",
                        },
                        {
                            deviceId: "default",
                            kind: "audiooutput",
                        },
                    ];
                },
            },
        },
    });
    const pyEnv = await startServer();
    pyEnv["res.partner"].create({ display_name: "Gwonam", phone: "515-555-0170" });
    pyEnv["res.users.settings"].create({
        how_to_call_on_mobile: "voip",
        user_id: pyEnv.currentUserId,
    });
    const { advanceTime } = await start({ hasTimeControl: true });
    await click(".o_menu_systray button[title='Open Softphone']");
    await click(".nav-link", { text: "Contacts" });
    await contains(".o-voip-ContactsTab b", { text: "Gwonam" });
    await click("button[title='Call']");
    await advanceTime(5000);
    await click("button[title='Change input device']:enabled");
    await contains("select[id='device-select']");
    await contains("option", { count: 2 });
});
