odoo.define('mail/static/src/models/thread/thread_tests.js', function (require) {
'use strict';

const { afterEach, beforeEach, start } = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail', {}, function () {
QUnit.module('models', {}, function () {
QUnit.module('thread', {}, function () {
QUnit.module('thread_tests.js', {
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
});

QUnit.test('inbox & starred mailboxes', async function (assert) {
    assert.expect(10);

    await this.start();
    const mailboxInbox = this.env.messaging.inbox;
    const mailboxStarred = this.env.messaging.starred;
    assert.ok(mailboxInbox, "should have mailbox inbox");
    assert.ok(mailboxStarred, "should have mailbox starred");
    assert.strictEqual(mailboxInbox.model, 'mail.box');
    assert.strictEqual(mailboxInbox.counter, 0);
    assert.strictEqual(mailboxInbox.id, 'inbox');
    assert.strictEqual(mailboxInbox.name, "Inbox"); // language-dependent
    assert.strictEqual(mailboxStarred.model, 'mail.box');
    assert.strictEqual(mailboxStarred.counter, 0);
    assert.strictEqual(mailboxStarred.id, 'starred');
    assert.strictEqual(mailboxStarred.name, "Starred"); // language-dependent
});

QUnit.test('create (channel)', async function (assert) {
    assert.expect(23);

    await this.start();
    assert.notOk(this.env.models['mail.partner'].find(partner => partner.id === 9));
    assert.notOk(this.env.models['mail.partner'].find(partner => partner.id === 10));
    assert.notOk(this.env.models['mail.thread'].find(thread =>
        thread.id === 100 &&
        thread.model === 'mail.channel'
    ));

    const thread = this.env.models['mail.thread'].create({
        channel_type: 'channel',
        id: 100,
        members: [['insert', [{
            email: "john@example.com",
            id: 9,
            name: "John",
        }, {
            email: "fred@example.com",
            id: 10,
            name: "Fred",
        }]]],
        message_needaction_counter: 6,
        model: 'mail.channel',
        name: "General",
        public: 'public',
        serverMessageUnreadCounter: 5,
    });
    assert.ok(thread);
    assert.ok(this.env.models['mail.partner'].find(partner => partner.id === 9));
    assert.ok(this.env.models['mail.partner'].find(partner => partner.id === 10));
    assert.ok(this.env.models['mail.thread'].find(thread =>
        thread.id === 100 &&
        thread.model === 'mail.channel'
    ));
    const partner9 = this.env.models['mail.partner'].find(partner => partner.id === 9);
    const partner10 = this.env.models['mail.partner'].find(partner => partner.id === 10);
    assert.strictEqual(thread, this.env.models['mail.thread'].find(thread =>
        thread.id === 100 &&
        thread.model === 'mail.channel'
    ));
    assert.strictEqual(thread.model, 'mail.channel');
    assert.strictEqual(thread.channel_type, 'channel');
    assert.strictEqual(thread.id, 100);
    assert.ok(thread.members.includes(partner9));
    assert.ok(thread.members.includes(partner10));
    assert.strictEqual(thread.message_needaction_counter, 6);
    assert.strictEqual(thread.name, "General");
    assert.strictEqual(thread.public, 'public');
    assert.strictEqual(thread.serverMessageUnreadCounter, 5);
    assert.strictEqual(partner9.email, "john@example.com");
    assert.strictEqual(partner9.id, 9);
    assert.strictEqual(partner9.name, "John");
    assert.strictEqual(partner10.email, "fred@example.com");
    assert.strictEqual(partner10.id, 10);
    assert.strictEqual(partner10.name, "Fred");
});

QUnit.test('create (chat)', async function (assert) {
    assert.expect(15);

    await this.start();
    assert.notOk(this.env.models['mail.partner'].find(partner => partner.id === 5));
    assert.notOk(this.env.models['mail.thread'].find(thread =>
        thread.id === 200 &&
        thread.model === 'mail.channel'
    ));

    const channel = this.env.models['mail.thread'].create({
        channel_type: 'chat',
        id: 200,
        members: [['insert', {
            email: "demo@example.com",
            id: 5,
            im_status: 'online',
            name: "Demo",
        }]],
        model: 'mail.channel',
    });
    assert.ok(channel);
    assert.ok(this.env.models['mail.thread'].find(thread =>
        thread.id === 200 &&
        thread.model === 'mail.channel'
    ));
    assert.ok(this.env.models['mail.partner'].find(partner => partner.id === 5));
    const partner = this.env.models['mail.partner'].find(partner => partner.id === 5);
    assert.strictEqual(channel, this.env.models['mail.thread'].find(thread =>
        thread.id === 200 &&
        thread.model === 'mail.channel'
    ));
    assert.strictEqual(channel.model, 'mail.channel');
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
});

});
