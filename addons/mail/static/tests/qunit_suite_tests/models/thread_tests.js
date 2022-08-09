/** @odoo-module **/

import { insert } from '@mail/model/model_field_command';
import { start } from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('models', {}, function () {
QUnit.module('thread_tests.js');

QUnit.test('inbox & starred mailboxes', async function (assert) {
    assert.expect(10);

    const { messaging } = await start();
    const mailboxInbox = messaging.inbox;
    const mailboxStarred = messaging.starred;
    assert.ok(mailboxInbox, "should have mailbox inbox");
    assert.ok(mailboxStarred, "should have mailbox starred");
    assert.strictEqual(mailboxInbox.thread.model, 'mail.box');
    assert.strictEqual(mailboxInbox.counter, 0);
    assert.strictEqual(mailboxInbox.thread.id, 'inbox');
    assert.strictEqual(mailboxInbox.name, "Inbox"); // language-dependent
    assert.strictEqual(mailboxStarred.thread.model, 'mail.box');
    assert.strictEqual(mailboxStarred.counter, 0);
    assert.strictEqual(mailboxStarred.thread.id, 'starred');
    assert.strictEqual(mailboxStarred.name, "Starred"); // language-dependent
});

QUnit.test('create (channel)', async function (assert) {
    assert.expect(20);

    const { messaging } = await start();
    assert.notOk(messaging.models['Partner'].findFromIdentifyingData({ id: 9 }));
    assert.notOk(messaging.models['Partner'].findFromIdentifyingData({ id: 10 }));
    assert.notOk(messaging.models['Channel'].findFromIdentifyingData({ id: 100 }));

    messaging.models['Thread'].insert({
        channel: {
            channel_type: 'channel',
            id: 100,
            serverMessageUnreadCounter: 5,
        },
        id: 100,
        members: insert([{
            email: "john@example.com",
            id: 9,
            name: "John",
        }, {
            email: "fred@example.com",
            id: 10,
            name: "Fred",
        }]),
        message_needaction_counter: 6,
        model: 'mail.channel',
        name: "General",
        public: 'public',
    });
    const channel = messaging.models['Channel'].findFromIdentifyingData({ id: 100 });
    assert.ok(channel);
    assert.ok(messaging.models['Partner'].findFromIdentifyingData({ id: 9 }));
    assert.ok(messaging.models['Partner'].findFromIdentifyingData({ id: 10 }));
    const partner9 = messaging.models['Partner'].findFromIdentifyingData({ id: 9 });
    const partner10 = messaging.models['Partner'].findFromIdentifyingData({ id: 10 });
    assert.strictEqual(channel.channel_type, 'channel');
    assert.strictEqual(channel.id, 100);
    assert.ok(channel.thread.members.includes(partner9));
    assert.ok(channel.thread.members.includes(partner10));
    assert.strictEqual(channel.thread.message_needaction_counter, 6);
    assert.strictEqual(channel.thread.name, "General");
    assert.strictEqual(channel.thread.public, 'public');
    assert.strictEqual(channel.serverMessageUnreadCounter, 5);
    assert.strictEqual(partner9.email, "john@example.com");
    assert.strictEqual(partner9.id, 9);
    assert.strictEqual(partner9.name, "John");
    assert.strictEqual(partner10.email, "fred@example.com");
    assert.strictEqual(partner10.id, 10);
    assert.strictEqual(partner10.name, "Fred");
});

QUnit.test('create (chat)', async function (assert) {
    assert.expect(12);

    const { messaging } = await start();
    assert.notOk(messaging.models['Partner'].findFromIdentifyingData({ id: 5 }));
    assert.notOk(messaging.models['Channel'].findFromIdentifyingData({ id: 200 }));

    messaging.models['Thread'].insert({
        channel: {
            channel_type: 'chat',
            id: 200,
        },
        id: 200,
        members: insert({
            email: "demo@example.com",
            id: 5,
            im_status: 'online',
            name: "Demo",
        }),
        model: 'mail.channel',
    });
    const channel = messaging.models['Channel'].findFromIdentifyingData({ id: 200 });
    assert.ok(channel);
    assert.ok(messaging.models['Partner'].findFromIdentifyingData({ id: 5 }));
    const partner = messaging.models['Partner'].findFromIdentifyingData({ id: 5 });
    assert.strictEqual(channel.channel_type, 'chat');
    assert.strictEqual(channel.id, 200);
    assert.ok(channel.correspondent);
    assert.strictEqual(partner, channel.correspondent);
    assert.strictEqual(partner.email, "demo@example.com");
    assert.strictEqual(partner.id, 5);
    assert.strictEqual(partner.im_status, 'online');
    assert.strictEqual(partner.name, "Demo");
});

});
});
