/** @odoo-module **/

import { afterEach, beforeEach, start } from '@mail/utils/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('models', {}, function () {
QUnit.module('messaging_menu', {}, function () {
QUnit.module('messaging_menu_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.start = async params => {
            const { env } = await start({ data: this.data, ...params });
            this.env = env;
        };
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('messaging menu counter should ignore unread messages in channels that are unpinned', async function (assert) {
    assert.expect(1);

    await this.start();
    this.messaging.models['mail.thread'].create({
        id: 31,
        isServerPinned: false,
        model: 'mail.channel',
        serverMessageUnreadCounter: 1,
    });
    assert.strictEqual(
        this.messaging.messagingMenu.counter,
        0,
        "messaging menu counter should ignore unread messages in channels that are unpinned"
    );
});

});
});
});
