/** @odoo-module **/

import { start, startServer } from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('models', {}, function () {
QUnit.module('messaging_tests.js', {}, function () {

QUnit.test('openChat: display notification for partner without user', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create();
    const { messaging } = await start({
        services: {
            notification: {
                notify(notification) {
                    assert.ok(
                        true,
                        "should display a toast notification after failing to open chat"
                    );
                    assert.strictEqual(
                        notification.message,
                        "You can only chat with partners that have a dedicated user.",
                        "should display the correct information in the notification"
                    );
                },
            },
        },
    });

    await messaging.openChat({ partnerId: resPartnerId1 });
});

QUnit.test('openChat: display notification for wrong user', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    pyEnv['res.users'].create();
    const { messaging } = await start({
        services: {
            notification: {
                notify(notification) {
                    assert.ok(
                        true,
                        "should display a toast notification after failing to open chat"
                    );
                    assert.strictEqual(
                        notification.message,
                        "You can only chat with existing users.",
                        "should display the correct information in the notification"
                    );
                },
            },
        },
    });

    // userId not in the server data
    await messaging.openChat({ userId: 4242 });
});

QUnit.test('openChat: open new chat for user', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create();
    pyEnv['res.users'].create({ partner_id: resPartnerId1 });

    const { messaging } = await start({ data: this.data });
    const existingChat = messaging.models['Thread'].find(thread =>
        thread.channel_type === 'chat' &&
        thread.correspondent &&
        thread.correspondent.id === resPartnerId1 &&
        thread.model === 'mail.channel' &&
        thread.public === 'private'
    );
    assert.notOk(existingChat, 'a chat should not exist with the target partner initially');

    await messaging.openChat({ partnerId: resPartnerId1 });
    const chat = messaging.models['Thread'].find(thread =>
        thread.channel_type === 'chat' &&
        thread.correspondent &&
        thread.correspondent.id === resPartnerId1 &&
        thread.model === 'mail.channel' &&
        thread.public === 'private'
    );
    assert.ok(chat, 'a chat should exist with the target partner');
    assert.strictEqual(chat.threadViews.length, 1, 'the chat should be displayed in a `ThreadView`');
});

QUnit.test('openChat: open existing chat for user', async function (assert) {
    assert.expect(5);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create();
    pyEnv['res.users'].create({ partner_id: resPartnerId1 });
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_last_seen_partner_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
        ],
        channel_type: "chat",
        public: 'private',
    });
    const { messaging } = await start();
    const existingChat = messaging.models['Thread'].find(thread =>
        thread.channel_type === 'chat' &&
        thread.correspondent &&
        thread.correspondent.id === resPartnerId1 &&
        thread.model === 'mail.channel' &&
        thread.public === 'private'
    );
    assert.ok(existingChat, 'a chat should initially exist with the target partner');
    assert.strictEqual(existingChat.threadViews.length, 0, 'the chat should not be displayed in a `ThreadView`');

    await messaging.openChat({ partnerId: resPartnerId1 });
    assert.ok(existingChat, 'a chat should still exist with the target partner');
    assert.strictEqual(existingChat.id, mailChannelId1, 'the chat should be the existing chat');
    assert.strictEqual(existingChat.threadViews.length, 1, 'the chat should now be displayed in a `ThreadView`');
});

});
});
});
