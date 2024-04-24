import {
    click,
    contains,
    defineMailModels,
    openDiscuss,
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
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Discuss-header .fa-gear");
    await contains(".o-discuss-CallSettings");
    await contains("label[aria-label='Input device']");
    await contains("option[value=mockAudioDeviceId]");
    await contains("option[value=mockVideoDeviceId]", { count: 0 });
    await contains("input[title='toggle push-to-talk']");
    await contains("label[aria-label='Voice detection threshold']");
    await contains("input[title='Show video participants only']");
    await contains("input[title='Blur video background']");
});

test("activate push to talk", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Discuss-header .fa-gear");
    await click("input[title='toggle push-to-talk']");
    await contains("i[aria-label='Register new key']");
    await contains("label[aria-label='Delay after releasing push-to-talk']");
    await contains("label[aria-label='Voice detection threshold']", { count: 0 });
});

test("activate blur", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Discuss-header .fa-gear");
    await click("input[title='Blur video background']");
    await contains("label[aria-label='Background blur intensity']");
    await contains("label[aria-label='Edge blur intensity']");
});

test("Inbox should not have any call settings menu", async () => {
    await startServer();
    await start();
    await openDiscuss("mail.box_inbox");
    await contains(".o-mail-Thread");
    await contains("button[title='Show Call Settings']", { count: 0 });
});

test("Call settings menu should not be visible on selecting a mailbox (from being open)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Show Call Settings']");
    await click("button", { text: "Inbox" });
    await contains("button[title='Hide Call Settings']", { count: 0 });
    await contains(".o-discuss-CallSettings", { count: 0 });
});
