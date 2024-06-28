import {
    click,
    contains,
    defineMailModels,
    patchUiSize,
    SIZES,
    start,
    startServer,
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
    pyEnv["discuss.channel"].create({ name: "test" });
    patchUiSize({ size: SIZES.SM });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "test" });
    await click("[title='Open Actions Menu']");
    await click(".o-mail-ChatWindow-command", { text: "Show Call Settings" });
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
    pyEnv["discuss.channel"].create({ name: "test" });
    patchUiSize({ size: SIZES.SM });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "test" });
    await click("[title='Open Actions Menu']");
    await click(".o-mail-ChatWindow-command", { text: "Show Call Settings" });
    await click("button", { text: "Push to Talk" });
    await contains("i[aria-label='Register new key']");
    await contains("label", { text: "Delay after releasing push-to-talk" });
    await contains("label", { text: "Voice detection threshold", count: 0 });
});

test("activate blur", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "test" });
    patchUiSize({ size: SIZES.SM });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem", { text: "test" });
    await click("[title='Open Actions Menu']");
    await click(".o-mail-ChatWindow-command", { text: "Show Call Settings" });
    await click("input[title='Blur video background']");
    await contains("label", { text: "Blur video background" });
    await contains("label", { text: "Edge blur intensity" });
});
