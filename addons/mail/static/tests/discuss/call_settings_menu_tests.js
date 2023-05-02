/* @odoo-module */

import { click, start, startServer } from "@mail/../tests/helpers/test_utils";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { browser } from "@web/core/browser/browser";

QUnit.module("call setting");

QUnit.test("Renders the call settings", async (assert) => {
    patchWithCleanup(browser, {
        navigator: {
            ...browser.navigator,
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
        },
    });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-mail-Discuss-header .fa-gear");
    assert.containsOnce($, ".o-discuss-CallSettings", "Should have a call settings menu");
    assert.containsOnce($, "label[aria-label='Input device']");
    assert.containsOnce($, "option[value=mockAudioDeviceId]");
    assert.containsNone($, "option[value=mockVideoDeviceId]");
    assert.containsOnce($, "input[title='toggle push-to-talk']");
    assert.containsOnce($, "label[aria-label='Voice detection threshold']");
    assert.containsOnce($, "input[title='Show video participants only']");
    assert.containsOnce($, "input[title='Blur video background']");
});

QUnit.test("activate push to talk", async (assert) => {
    patchWithCleanup(browser, {
        navigator: {
            ...browser.navigator,
            mediaDevices: {
                enumerateDevices: () => Promise.resolve([]),
            },
        },
    });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-mail-Discuss-header .fa-gear");
    await click("input[title='toggle push-to-talk']");
    assert.containsOnce($, "i[aria-label='Register new key']");
    assert.containsOnce($, "label[aria-label='Delay after releasing push-to-talk']");
    assert.containsNone($, "label[aria-label='Voice detection threshold']");
});

QUnit.test("activate blur", async (assert) => {
    patchWithCleanup(browser, {
        navigator: {
            ...browser.navigator,
            mediaDevices: {
                enumerateDevices: () => Promise.resolve([]),
            },
        },
    });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    const { click, openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-mail-Discuss-header .fa-gear");
    await click("input[title='Blur video background']");
    assert.containsOnce($, "label[aria-label='Background blur intensity']");
    assert.containsOnce($, "label[aria-label='Edge blur intensity']");
});

QUnit.test("Inbox should not have any call settings menu", async (assert) => {
    await startServer();
    const { openDiscuss } = await start();
    await openDiscuss("mail.box_inbox");
    assert.containsNone($, "button[title='Show Call Settings']");
});

QUnit.test(
    "Call settings menu should not be visible on selecting a mailbox (from being open)",
    async (assert) => {
        patchWithCleanup(browser, {
            navigator: {
                ...browser.navigator,
                mediaDevices: {
                    enumerateDevices: () => Promise.resolve([]),
                },
            },
        });
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ name: "General" });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        await click("button[title='Show Call Settings']");
        await click("button:contains(Inbox)");
        assert.containsNone($, "button[title='Hide Call Settings']");
        assert.containsNone($, ".o-discuss-CallSettings");
    }
);
