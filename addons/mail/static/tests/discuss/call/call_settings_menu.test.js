import {
    assertSteps,
    click,
    contains,
    defineMailModels,
    openDiscuss,
    patchUiSize,
    SIZES,
    start,
    startServer,
    step,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

import { browser } from "@web/core/browser/browser";

describe.current.tags("desktop");
defineMailModels();

test("Renders the call settings", async () => {
    patchWithCleanup(browser.navigator, {
        mediaDevices: {
            enumerateDevices: () =>
                Promise.resolve([
                    {
                        deviceId: "mockAudioDeviceId",
                        kind: "audioinput",
                        label: "mockAudioDeviceLabel",
                    },
                    {
                        deviceId: "mockVideoDeviceId",
                        kind: "videoinput",
                        label: "mockVideoDeviceLabel",
                    },
                ]),
        },
    });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item", { text: "Call Settings" });
    await contains(".o-discuss-CallSettings");
    await contains("label[aria-label='Input device']");
    await contains("option[value=mockAudioDeviceId]");
    await contains("option[value=mockVideoDeviceId]", { count: 0 });
    await contains("button", { text: "Voice Detection" });
    await contains("button", { text: "Push to Talk" });
    await contains("label", { text: "Voice detection threshold" });
    await contains("label", { text: "Show video participants only" });
    await contains("label", { text: "Blur video background" });
});

test("activate push to talk", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item", { text: "Call Settings" });
    await click("button", { text: "Push to Talk" });
    await contains("i[aria-label='Register new key']");
    await contains("label", { text: "Delay after releasing push-to-talk" });
    await contains("label", { text: "Voice detection threshold", count: 0 });
});

test("activate blur", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item", { text: "Call Settings" });
    await click("input[title='Blur video background']");
    await contains("label", { text: "Blur video background" });
    await contains("label", { text: "Edge blur intensity" });
});

test("local storage for call settings", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    patchWithCleanup(browser.localStorage, {
        getItem(key) {
            if (key === "mail_user_setting_background_blur_amount") {
                return "3";
            }
            if (key === "mail_user_setting_edge_blur_amount") {
                return "5";
            }
            if (key === "mail_user_setting_show_only_video") {
                return "true";
            }
            if (key === "mail_user_setting_use_blur") {
                return "true";
            }
            return super.getItem(key);
        },
        setItem(key, value) {
            if (key.startsWith("mail_user_setting")) {
                step(`${key}: ${value}`);
            }
            return super.setItem(key, value);
        },
    });
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    // testing load from local storage
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item", { text: "Call Settings" });
    await contains("input[title='Show video participants only']:checked");
    await contains("input[title='Blur video background']:checked");
    await contains("label[title='Background blur intensity']", { text: "15%" });
    await contains("label[title='Edge blur intensity']", { text: "25%" });

    // testing save to local storage
    await click("input[title='Show video participants only']");
    await assertSteps(["mail_user_setting_show_only_video: false"]);
    await click("input[title='Blur video background']");
    await assertSteps(["mail_user_setting_use_blur: false"]);
});
