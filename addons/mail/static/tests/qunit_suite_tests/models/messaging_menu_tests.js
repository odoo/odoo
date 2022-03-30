/** @odoo-module **/

import { start } from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('models', {}, function () {
QUnit.module('messaging_menu_tests.js');

QUnit.test('messaging menu counter should ignore unread messages in channels that are unpinned', async function (assert) {
    assert.expect(1);

    const { messaging } = await start();
    messaging.models['Thread'].create({
        id: 31,
        isServerPinned: false,
        model: 'mail.channel',
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
