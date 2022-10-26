/** @odoo-module **/

import {
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';
import { browser } from '@web/core/browser/browser';
import { patchWithCleanup } from '@web/../tests/helpers/utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('call_settings_menu_tests.js');

QUnit.test('Renders the call settings', async function (assert) {
    assert.expect(9);

    patchWithCleanup(browser, {
        navigator: {
            ...browser.navigator,
            mediaDevices: {
                enumerateDevices: () => Promise.resolve([
                    { deviceId: 'mockAudioDeviceId', kind: 'audioinput', label: 'mockAudioDeviceLabel' },
                    { deviceId: 'mockVideoDeviceId', kind: 'videoinput', label: 'mockVideoDeviceLabel' },
                ]),
            },
        }
    });

    const pyEnv = await startServer();
    const mailChannelId = pyEnv['mail.channel'].create({});
    const { click, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId}`,
            },
        },
    });
    await openDiscuss();
    await click('.o_ThreadViewTopbar_openCallSettingsButton');

    assert.containsOnce(
        document.body,
        '.o_CallSettingsMenu',
        "Should have a call settings menu"
    );
    assert.containsN(
        document.body,
        '.o_CallSettingsMenu_option',
        5,
        "Should have five options",
    );

    assert.containsOnce(
        document.body,
        '.o_CallSettingsMenu_optionDeviceSelect',
        "should have an audio device selection",
    );
    assert.containsOnce(
        document.body,
        'option[value=mockAudioDeviceId]',
        "should have an option to select an audio input device",
    );
    assert.containsNone(
        document.body,
        'option[value=mockVideoDeviceId]',
        "should not have an option to select a video input device",
    );
    assert.containsOnce(
        document.body,
        '.o_CallSettingsMenu_pushToTalkOption',
        "should have an option to toggle push-to-talk",
    );
    assert.containsOnce(
        document.body,
        '.o_CallSettingsMenu_voiceThresholdOption',
        "should have an option to set the voice detection threshold",
    );
    assert.containsOnce(
        document.body,
        '.o_CallSettingsMenu_showOnlyVideoOption',
        "should have an option to filter participants who have no video",
    );
    assert.containsOnce(
        document.body,
        '.o_CallSettingsMenu_blurOption',
        "should have an option to toggle the background blur feature",
    );
});

QUnit.test('activate push to talk', async function (assert) {
    assert.expect(3);

    patchWithCleanup(browser, {
        navigator: {
            ...browser.navigator,
            mediaDevices: {
                enumerateDevices: () => Promise.resolve([]),
            },
        }
    });

    const pyEnv = await startServer();
    const mailChannelId = pyEnv['mail.channel'].create({});
    const { click, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId}`,
            },
        },
    });
    await openDiscuss();
    await click('.o_ThreadViewTopbar_openCallSettingsButton');
    await click('.o_CallSettingsMenu_pushToTalkOption');

    assert.containsOnce(
        document.body,
        '.o_CallSettingsMenu_pushToTalkKeyOption',
        "should have an option set the push to talk shortcut key",
    );
    assert.containsOnce(
        document.body,
        '.o_CallSettingsMenu_pushToTalkDelayOption',
        "should have an option to set the push-to-talk delay",
    );
    assert.containsNone(
        document.body,
        '.o_CallSettingsMenu_voiceThresholdOption',
        "should not have an option to set the voice detection threshold",
    );
});

QUnit.test('activate blur', async function (assert) {
    assert.expect(2);

    patchWithCleanup(browser, {
        navigator: {
            ...browser.navigator,
            mediaDevices: {
                enumerateDevices: () => Promise.resolve([]),
            },
        }
    });

    const pyEnv = await startServer();
    const mailChannelId = pyEnv['mail.channel'].create({});
    const { click, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId}`,
            },
        },
    });
    await openDiscuss();
    await click('.o_ThreadViewTopbar_openCallSettingsButton');
    await click('.o_CallSettingsMenu_blurOption');

    assert.containsOnce(
        document.body,
        '.o_CallSettingsMenu_backgroundBlurIntensityOption',
        "should have an option set the background blur intensity",
    );
    assert.containsOnce(
        document.body,
        '.o_CallSettingsMenu_edgeBlurIntensityOption',
        "should have an option to set the edge blur intensity",
    );
});

});
});
