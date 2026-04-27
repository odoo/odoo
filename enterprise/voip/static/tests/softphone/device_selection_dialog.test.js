import { describe, test } from "@odoo/hoot";
import { advanceTime } from "@odoo/hoot-mock";
import { Store } from "@mail/core/common/store_service";
import { click, contains, start, startServer } from "@mail/../tests/mail_test_helpers";
import { setupVoipTests } from "@voip/../tests/voip_test_helpers";
import { browser } from "@web/core/browser/browser";
import { patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("mobile");
setupVoipTests();

test("Switch audio input", async () => {
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
    pyEnv["res.partner"].create({ name: "Gwonam", phone: "515-555-0170" });
    pyEnv["res.users.settings"].create({
        how_to_call_on_mobile: "voip",
        user_id: serverState.userId,
    });
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await advanceTime(Store.FETCH_DATA_DEBOUNCE_DELAY);
    await click(".nav-link", { text: "Contacts" });
    await contains(".o-voip-ContactsTab b", { text: "Gwonam" });
    await click("button[title='Call']");
    await contains(".o-voip-CorrespondenceDetails");
    await advanceTime(3000);
    await click("button[title='Change input device']:enabled");
    await contains("select[id='device-select']");
    await contains("option", { count: 2 });
});
