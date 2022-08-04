/** @odoo-module **/

import { start } from '@mail/../tests/helpers/test_utils';

import { browser } from '@web/core/browser/browser';
import { patchWithCleanup } from '@web/../tests/helpers/utils';
import { insertAndReplace } from '@mail/model/model_field_command';

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
    messaging.models['Channel'].insert({
        id: 31,
        isServerPinned: false,
        serverMessageUnreadCounter: 1,
    });
    assert.strictEqual(
        messaging.messagingMenu.counter,
        0,
        "messaging menu counter should ignore unread messages in channels that are unpinned"
    );
});

});
});
