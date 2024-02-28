/** @odoo-module **/

import { start } from '@mail/../tests/helpers/test_utils';

import { browser } from '@web/core/browser/browser';
import { patchWithCleanup } from '@web/../tests/helpers/utils';

QUnit.module('mail', {}, function () {
QUnit.module('models', {}, function () {
QUnit.module('messaging_menu_tests.js');

QUnit.test('messaging menu counter should ignore unread messages in channels that are unpinned', async function (assert) {
    assert.expect(1);

    patchWithCleanup(browser, {
        Notification: {
            ...browser.Notification,
            permission: 'denied',
        },
    });
    const { messaging } = await start();
    messaging.models['Thread'].insert({
        channel: {
            id: 31,
            serverMessageUnreadCounter: 1,
        },
        id: 31,
        isServerPinned: false,
        model: 'mail.channel',
    });
    assert.strictEqual(
        messaging.messagingMenu.counter,
        0,
        "messaging menu counter should ignore unread messages in channels that are unpinned"
    );
});

});
});
