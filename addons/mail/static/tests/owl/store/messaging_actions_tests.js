odoo.define('mail.store.ActionsTests', function (require) {
'use strict';

const {
    afterEach: utilsAfterEach,
    beforeEach: utilsBeforeEach,
    pause,
    start: utilsStart,
} = require('mail.messagingTestUtils');

QUnit.module('mail.messaging', {}, function () {
QUnit.module('store', {}, function () {
QUnit.module('Actions', {
    beforeEach() {
        utilsBeforeEach(this);
        this.start = async params => {
            if (this.widget) {
                this.widget.destroy();
            }
            let { env, widget } = await utilsStart(Object.assign({}, params, {
                data: this.data,
            }));
            this.env = env;
            this.widget = widget;
            this.store = env.store;
            this.state = this.store.state;
        };
    },
    afterEach() {
        utilsAfterEach(this);
        this.env = undefined;
        if (this.widget) {
            this.widget.destroy();
            this.widget = undefined;
        }
    }
});

QUnit.test('createAttachment: txt', async function (assert) {
    assert.expect(10);

    await this.start();
    assert.notOk(this.state.attachments['ir.attachment_750']);

    const attachmentLocalId = this.store.dispatch('createAttachment', {
        filename: "test.txt",
        id: 750,
        mimetype: 'text/plain',
        name: "test.txt",
    });
    const attachment = this.state.attachments[attachmentLocalId];
    assert.strictEqual(attachmentLocalId, 'ir.attachment_750');
    assert.ok(attachment);
    assert.strictEqual(attachment._model, 'ir.attachment');
    assert.strictEqual(attachment.filename, "test.txt");
    assert.strictEqual(attachment.id, 750);
    assert.notOk(attachment.isTemporary);
    assert.strictEqual(attachment.localId, 'ir.attachment_750');
    assert.strictEqual(attachment.mimetype, 'text/plain');
    assert.strictEqual(attachment.name, "test.txt");
});

QUnit.test('createMessage', async function (assert) {
    assert.expect(34);

    await this.start({
        session: {
            partner_id: 3,
        }
    });
    assert.notOk(this.state.partners['res.partner_5']);
    assert.notOk(this.state.threads['mail.channel_100']);
    assert.notOk(this.state.attachments['ir.attachment_750']);
    assert.notOk(this.state.messages['mail.message_4000']);

    const messageLocalId = this.store.dispatch('_createMessage', {
        attachment_ids: [{
            filename: "test.txt",
            id: 750,
            mimetype: 'text/plain',
            name: "test.txt",
        }],
        author_id: [5, "Demo"],
        body: "<p>Test</p>",
        channel_ids: [100],
        date: "2019-05-05 10:00:00",
        id: 4000,
        model: 'mail.channel',
        needaction_partner_ids: [2, 3],
        record_name: "General",
        starred_partner_ids: [3, 4],
        res_id: 100,
    });
    const message = this.state.messages[messageLocalId];
    assert.strictEqual(messageLocalId, 'mail.message_4000');
    assert.ok(message);
    assert.strictEqual(message._model, 'mail.message');
    assert.strictEqual(message.body, "<p>Test</p>");
    assert.ok(message.date instanceof moment);
    assert.strictEqual(
        moment(message.date).utc().format('YYYY-MM-DD hh:mm:ss'),
        "2019-05-05 10:00:00");
    assert.strictEqual(message.id, 4000);
    assert.strictEqual(message.localId, 'mail.message_4000');
    assert.strictEqual(message.originThreadLocalId, 'mail.channel_100');
    assert.ok(message.threadLocalIds.includes('mail.channel_100'));
    assert.ok(message.threadLocalIds.includes('mail.box_inbox')); // from partnerId being in needaction_partner_ids
    assert.ok(message.threadLocalIds.includes('mail.box_starred')); // from partnerId being in starred_partner_ids
    const attachment = this.state.attachments['ir.attachment_750'];
    assert.ok(attachment);
    assert.strictEqual(attachment._model, 'ir.attachment');
    assert.strictEqual(attachment.filename, "test.txt");
    assert.strictEqual(attachment.id, 750);
    assert.notOk(attachment.isTemporary);
    assert.strictEqual(attachment.localId, 'ir.attachment_750');
    assert.strictEqual(attachment.mimetype, 'text/plain');
    assert.strictEqual(attachment.name, "test.txt");
    const thread = this.state.threads['mail.channel_100'];
    assert.ok(thread);
    assert.strictEqual(thread._model, 'mail.channel');
    assert.strictEqual(thread.id, 100);
    assert.strictEqual(thread.localId, 'mail.channel_100');
    assert.strictEqual(thread.name, "General");
    const partner = this.state.partners['res.partner_5'];
    assert.ok(partner);
    assert.strictEqual(partner._model, 'res.partner');
    assert.strictEqual(partner.display_name, "Demo");
    assert.strictEqual(partner.id, 5);
    assert.strictEqual(partner.localId, 'res.partner_5');
});

QUnit.test('createThread: channel', async function (assert) {
    assert.expect(26);

    await this.start();
    assert.notOk(this.state.partners['res.partner_9']);
    assert.notOk(this.state.partners['res.partner_10']);
    assert.notOk(this.state.threads['mail.channel_100']);

    const threadLocalId = this.store.dispatch('_createThread', {
        channel_type: 'channel',
        id: 100,
        members: [{
            email: "john@example.com",
            id: 9,
            name: "John",
        }, {
            email: "fred@example.com",
            id: 10,
            name: "Fred",
        }],
        message_needaction_counter: 6,
        message_unread_counter: 5,
        name: "General",
        public: 'public',
    });
    const thread = this.state.threads[threadLocalId];
    assert.strictEqual(threadLocalId, 'mail.channel_100');
    assert.ok(thread);
    assert.strictEqual(thread._model, 'mail.channel');
    assert.strictEqual(thread.channel_type, 'channel');
    assert.strictEqual(thread.id, 100);
    assert.strictEqual(thread.localId, 'mail.channel_100');
    assert.deepEqual(thread.members, [{
        email: "john@example.com",
        id: 9,
        name: "John",
    }, {
        email: "fred@example.com",
        id: 10,
        name: "Fred",
    }]);
    assert.strictEqual(thread.message_needaction_counter, 6);
    assert.strictEqual(thread.message_unread_counter, 5);
    assert.strictEqual(thread.name, "General");
    assert.strictEqual(thread.public, 'public');
    const partner9 = this.state.partners['res.partner_9'];
    const partner10 = this.state.partners['res.partner_10'];
    assert.ok(partner9);
    assert.strictEqual(partner9._model, 'res.partner');
    assert.strictEqual(partner9.email, "john@example.com");
    assert.strictEqual(partner9.id, 9);
    assert.strictEqual(partner9.localId, 'res.partner_9');
    assert.strictEqual(partner9.name, "John");
    assert.ok(partner10);
    assert.strictEqual(partner10._model, 'res.partner');
    assert.strictEqual(partner10.email, "fred@example.com");
    assert.strictEqual(partner10.id, 10);
    assert.strictEqual(partner10.localId, 'res.partner_10');
    assert.strictEqual(partner10.name, "Fred");
});

QUnit.test('createThread: chat', async function (assert) {
    assert.expect(16);

    await this.start();
    assert.notOk(this.state.partners['res.partner_5']);
    assert.notOk(this.state.threads['mail.channel_200']);

    const threadLocalId = this.store.dispatch('_createThread', {
        channel_type: 'chat',
        direct_partner: [{
            email: "demo@example.com",
            id: 5,
            im_status: 'online',
            name: "Demo",
        }],
        id: 200,
    });
    const thread = this.state.threads[threadLocalId];
    assert.strictEqual(threadLocalId, 'mail.channel_200');
    assert.ok(thread);
    assert.strictEqual(thread._model, 'mail.channel');
    assert.strictEqual(thread.channel_type, 'chat');
    assert.strictEqual(thread.id, 200);
    assert.strictEqual(thread.localId, 'mail.channel_200');
    assert.ok(thread.directPartnerLocalId);
    const directPartner = this.state.partners['res.partner_5'];
    assert.ok(directPartner);
    assert.strictEqual(directPartner._model, 'res.partner');
    assert.strictEqual(directPartner.email, "demo@example.com");
    assert.strictEqual(directPartner.id, 5);
    assert.strictEqual(directPartner.im_status, 'online');
    assert.strictEqual(directPartner.localId, 'res.partner_5');
    assert.strictEqual(directPartner.name, "Demo");
});

QUnit.test('saveChatWindowScrollTop', async function (assert) {
    assert.expect(3);
    await this.start();
    assert.strictEqual(
        Object.keys(this.state.chatWindowManager.chatWindowInitialScrollTops).length,
        0,
        "should not have initial scroll positions for any chat window initially"
    );
    this.store.dispatch('saveChatWindowScrollTop', 'mail.channel_1', 42);
    const chatWindowInitialScrollTops = this.state.chatWindowManager.chatWindowInitialScrollTops;
    assert.ok(
        chatWindowInitialScrollTops['mail.channel_1'] !== undefined,
        "Should have saved scroll positions for 'mail.channel_1'"
    );
    assert.strictEqual(
        chatWindowInitialScrollTops['mail.channel_1'],
        42,
        "Should have saved correct scroll positions for 'mail.channel_1'"
    );
});

QUnit.test('setChatWindowManagerNotifiedAutofocusCounter', async function (assert) {
    assert.expect(2);
    await this.start();
    assert.strictEqual(
        this.state.chatWindowManager.notifiedAutofocusCounter,
        0,
        "Initial value of notifiedAutofocusCounter is 0"
    );
    this.store.dispatch('setChatWindowManagerNotifiedAutofocusCounter', 42);
    assert.strictEqual(
        this.state.chatWindowManager.notifiedAutofocusCounter,
        42,
        "notifiedAutofocusCounter has been updated to 42"
    );
});

});
});
});
