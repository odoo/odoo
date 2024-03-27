import { describe, test } from "@odoo/hoot";

import { browser } from "@web/core/browser/browser";
import {
    click,
    contains,
    defineMailModels,
    openDiscuss,
    patchUiSize,
    SIZES,
    start,
    startServer,
} from "../../mail_test_helpers";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

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
    await contains(".o-mail-ChatWindow");
    await click(".o-mail-ChatWindow-command", { text: "test" });
    await click(".o-mail-ChatWindow-command", { text: "Show Settings" });
    await contains(".o-discuss-SettingsMenu");
    await contains("label", { text: "Input device" });
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
    await contains(".o-mail-ChatWindow");
    await click(".o-mail-ChatWindow-command", { text: "test" });
    await click(".o-mail-ChatWindow-command", { text: "Show Settings" });
    await click("button", { text: "Push to Talk" });
    await contains("label", { text: "Push-to-talk key" });
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
    await contains(".o-mail-ChatWindow");
    await click(".o-mail-ChatWindow-command", { text: "test" });
    await click(".o-mail-ChatWindow-command", { text: "Show Settings" });
    await click("input[title='Blur video background']");
    await contains("label", { text: "Blur video background" });
    await contains("label", { text: "Edge blur intensity" });
});

test("Inbox should not have any call settings menu", async () => {
    await startServer();
    await start();
    await openDiscuss("mail.box_inbox");
    await contains(".o-mail-Thread");
    await contains("button[title='Show Settings']", { count: 0 });
});

test("Discuss should not have any call settings menu", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Thread");
    await contains("button[title='Show Settings']", { count: 0 });
});
