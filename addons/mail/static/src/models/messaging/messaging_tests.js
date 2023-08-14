odoo.define('mail/static/src/models/messaging/messaging_tests.js', function (require) {
'use strict';

const { afterEach, beforeEach, start } = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail', {}, function () {
QUnit.module('models', {}, function () {
QUnit.module('messaging', {}, function () {
QUnit.module('messaging_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.start = async params => {
            const { env, widget } = await start(Object.assign({}, params, {
                data: this.data,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        afterEach(this);
    },
}, function () {

QUnit.test('openChat: display notification for partner without user', async function (assert) {
    assert.expect(2);

    this.data['res.partner'].records.push({ id: 14 });
    await this.start();

    await this.env.messaging.openChat({ partnerId: 14 });
    assert.containsOnce(
        document.body,
        '.toast .o_notification_content',
        "should display a toast notification after failing to open chat"
    );
    assert.strictEqual(
        document.querySelector('.o_notification_content').textContent,
        "You can only chat with partners that have a dedicated user.",
        "should display the correct information in the notification"
    );
});

QUnit.test('openChat: display notification for wrong user', async function (assert) {
    assert.expect(2);

    await this.start();

    // user id not in this.data
    await this.env.messaging.openChat({ userId: 14 });
    assert.containsOnce(
        document.body,
        '.toast .o_notification_content',
        "should display a toast notification after failing to open chat"
    );
    assert.strictEqual(
        document.querySelector('.o_notification_content').textContent,
        "You can only chat with existing users.",
        "should display the correct information in the notification"
    );
});

QUnit.test('openChat: open new chat for user', async function (assert) {
    assert.expect(3);

    this.data['res.partner'].records.push({ id: 14 });
    this.data['res.users'].records.push({ id: 11, partner_id: 14 });
    await this.start();

    const existingChat = this.env.models['mail.thread'].find(thread =>
        thread.channel_type === 'chat' &&
        thread.correspondent &&
        thread.correspondent.id === 14 &&
        thread.model === 'mail.channel' &&
        thread.public === 'private'
    );
    assert.notOk(existingChat, 'a chat should not exist with the target partner initially');

    await this.env.messaging.openChat({ partnerId: 14 });
    const chat = this.env.models['mail.thread'].find(thread =>
        thread.channel_type === 'chat' &&
        thread.correspondent &&
        thread.correspondent.id === 14 &&
        thread.model === 'mail.channel' &&
        thread.public === 'private'
    );
    assert.ok(chat, 'a chat should exist with the target partner');
    assert.strictEqual(chat.threadViews.length, 1, 'the chat should be displayed in a `mail.thread_view`');
});

QUnit.test('openChat: open existing chat for user', async function (assert) {
    assert.expect(5);

    this.data['res.partner'].records.push({ id: 14 });
    this.data['res.users'].records.push({ id: 11, partner_id: 14 });
    this.data['mail.channel'].records.push({
        channel_type: "chat",
        id: 10,
        members: [this.data.currentPartnerId, 14],
        public: 'private',
    });
    await this.start();
    const existingChat = this.env.models['mail.thread'].find(thread =>
        thread.channel_type === 'chat' &&
        thread.correspondent &&
        thread.correspondent.id === 14 &&
        thread.model === 'mail.channel' &&
        thread.public === 'private'
    );
    assert.ok(existingChat, 'a chat should initially exist with the target partner');
    assert.strictEqual(existingChat.threadViews.length, 0, 'the chat should not be displayed in a `mail.thread_view`');

    await this.env.messaging.openChat({ partnerId: 14 });
    assert.ok(existingChat, 'a chat should still exist with the target partner');
    assert.strictEqual(existingChat.id, 10, 'the chat should be the existing chat');
    assert.strictEqual(existingChat.threadViews.length, 1, 'the chat should now be displayed in a `mail.thread_view`');
});

});

});
});
});

});
