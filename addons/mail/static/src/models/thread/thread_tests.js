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
    const mailboxInbox = this.env.messaging.__mfield_inbox();
    const mailboxStarred = this.env.messaging.__mfield_starred();
    assert.ok(mailboxInbox, "should have mailbox inbox");
    assert.ok(mailboxStarred, "should have mailbox starred");
    assert.strictEqual(mailboxInbox.__mfield_model(), 'mail.box');
    assert.strictEqual(mailboxInbox.__mfield_counter(), 0);
    assert.strictEqual(mailboxInbox.__mfield_id(), 'inbox');
    assert.strictEqual(mailboxInbox.__mfield_name(), "Inbox"); // language-dependent
    assert.strictEqual(mailboxStarred.__mfield_model(), 'mail.box');
    assert.strictEqual(mailboxStarred.__mfield_counter(), 0);
    assert.strictEqual(mailboxStarred.__mfield_id(), 'starred');
    assert.strictEqual(mailboxStarred.__mfield_name(), "Starred"); // language-dependent
});

QUnit.test('create (channel)', async function (assert) {
    assert.expect(23);

    await this.start();
    assert.notOk(this.env.models['mail.partner'].find(partner => partner.__mfield_id() === 9));
    assert.notOk(this.env.models['mail.partner'].find(partner => partner.__mfield_id() === 10));
    assert.notOk(this.env.models['mail.thread'].find(thread =>
        thread.__mfield_id() === 100 &&
        thread.__mfield_model() === 'mail.channel'
    ));

    const thread = this.env.models['mail.thread'].create({
        __mfield_channel_type: 'channel',
        __mfield_id: 100,
        __mfield_members: [['insert', [{
            __mfield_email: "john@example.com",
            __mfield_id: 9,
            __mfield_name: "John",
        }, {
            __mfield_email: "fred@example.com",
            __mfield_id: 10,
            __mfield_name: "Fred",
        }]]],
        __mfield_message_needaction_counter: 6,
        __mfield_model: 'mail.channel',
        __mfield_name: "General",
        __mfield_public: 'public',
        __mfield_serverMessageUnreadCounter: 5,
    });
    assert.ok(thread);
    assert.ok(this.env.models['mail.partner'].find(partner => partner.__mfield_id() === 9));
    assert.ok(this.env.models['mail.partner'].find(partner => partner.__mfield_id() === 10));
    assert.ok(this.env.models['mail.thread'].find(thread =>
        thread.__mfield_id() === 100 &&
        thread.__mfield_model() === 'mail.channel'
    ));
    const partner9 = this.env.models['mail.partner'].find(partner => partner.__mfield_id() === 9);
    const partner10 = this.env.models['mail.partner'].find(partner => partner.__mfield_id() === 10);
    assert.strictEqual(thread, this.env.models['mail.thread'].find(thread =>
        thread.__mfield_id() === 100 &&
        thread.__mfield_model() === 'mail.channel'
    ));
    assert.strictEqual(thread.__mfield_model(), 'mail.channel');
    assert.strictEqual(thread.__mfield_channel_type(), 'channel');
    assert.strictEqual(thread.__mfield_id(), 100);
    assert.ok(thread.__mfield_members().includes(partner9));
    assert.ok(thread.__mfield_members().includes(partner10));
    assert.strictEqual(thread.__mfield_message_needaction_counter(), 6);
    assert.strictEqual(thread.__mfield_name(), "General");
    assert.strictEqual(thread.__mfield_public(), 'public');
    assert.strictEqual(thread.__mfield_serverMessageUnreadCounter(), 5);
    assert.strictEqual(partner9.__mfield_email(), "john@example.com");
    assert.strictEqual(partner9.__mfield_id(), 9);
    assert.strictEqual(partner9.__mfield_name(), "John");
    assert.strictEqual(partner10.__mfield_email(), "fred@example.com");
    assert.strictEqual(partner10.__mfield_id(), 10);
    assert.strictEqual(partner10.__mfield_name(), "Fred");
});

QUnit.test('create (chat)', async function (assert) {
    assert.expect(15);

    await this.start();
    assert.notOk(this.env.models['mail.partner'].find(partner => partner.__mfield_id() === 5));
    assert.notOk(this.env.models['mail.thread'].find(thread =>
        thread.__mfield_id() === 200 &&
        thread.__mfield_model() === 'mail.channel'
    ));

    const channel = this.env.models['mail.thread'].create({
        __mfield_channel_type: 'chat',
        __mfield_id: 200,
        __mfield_members: [['insert', {
            __mfield_email: "demo@example.com",
            __mfield_id: 5,
            __mfield_im_status: 'online',
            __mfield_name: "Demo",
        }]],
        __mfield_model: 'mail.channel',
    });
    assert.ok(channel);
    assert.ok(this.env.models['mail.thread'].find(thread =>
        thread.__mfield_id() === 200 &&
        thread.__mfield_model() === 'mail.channel'
    ));
    assert.ok(this.env.models['mail.partner'].find(partner => partner.__mfield_id() === 5));
    const partner = this.env.models['mail.partner'].find(partner => partner.__mfield_id() === 5);
    assert.strictEqual(channel, this.env.models['mail.thread'].find(thread =>
        thread.__mfield_id() === 200 &&
        thread.__mfield_model() === 'mail.channel'
    ));
    assert.strictEqual(channel.__mfield_model(), 'mail.channel');
    assert.strictEqual(channel.__mfield_channel_type(), 'chat');
    assert.strictEqual(channel.__mfield_id(), 200);
    assert.ok(channel.__mfield_correspondent());
    assert.strictEqual(partner, channel.__mfield_correspondent());
    assert.strictEqual(partner.__mfield_email(), "demo@example.com");
    assert.strictEqual(partner.__mfield_id(), 5);
    assert.strictEqual(partner.__mfield_im_status(), 'online');
    assert.strictEqual(partner.__mfield_name(), "Demo");
});

});
});
});

});
