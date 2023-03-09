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
    const channelId = pyEnv["mail.channel"].create({ name: "test" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-mail-discuss-header .fa-gear");
    assert.containsOnce($, ".o-mail-call-settings", "Should have a call settings menu");
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
    const channelId = pyEnv["mail.channel"].create({ name: "test" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-mail-discuss-header .fa-gear");
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
    const channelId = pyEnv["mail.channel"].create({ name: "test" });
    const { click, openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-mail-discuss-header .fa-gear");
    await click("input[title='Blur video background']");
    assert.containsOnce($, "label[aria-label='Background blur intensity']");
    assert.containsOnce($, "label[aria-label='Edge blur intensity']");
});
