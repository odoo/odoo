/* @odoo-module */

import { click, start, startServer } from "@mail/../tests/helpers/test_utils";
import { getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { browser } from "@web/core/browser/browser";

let target;
QUnit.module("call setting", {
    async beforeEach() {
        target = getFixture();
    },
});

QUnit.test("Renders the call settings", async function (assert) {
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
    assert.containsOnce(target, ".o-mail-call-settings", "Should have a call settings menu");
    assert.containsOnce(target, "label[aria-label='Input device']");
    assert.containsOnce(target, "option[value=mockAudioDeviceId]");
    assert.containsNone(target, "option[value=mockVideoDeviceId]");
    assert.containsOnce(target, "input[title='toggle push-to-talk']");
    assert.containsOnce(target, "label[aria-label='Voice detection threshold']");
    assert.containsOnce(target, "input[title='Show video participants only']");
    assert.containsOnce(target, "input[title='Blur video background']");
});

QUnit.test("activate push to talk", async function (assert) {
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
    assert.containsOnce(target, "i[aria-label='Register new key']");
    assert.containsOnce(target, "label[aria-label='Delay after releasing push-to-talk']");
    assert.containsNone(target, "label[aria-label='Voice detection threshold']");
});

QUnit.test("activate blur", async function (assert) {
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
    assert.containsOnce(target, "label[aria-label='Background blur intensity']");
    assert.containsOnce(target, "label[aria-label='Edge blur intensity']");
});
