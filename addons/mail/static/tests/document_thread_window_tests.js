odoo.define('mail.documentThreadWindowTests', function (require) {
"use strict";

var mailTestUtils = require('mail.testUtils');
var MessagingMenu = require('mail.systray.MessagingMenu');

var testUtils = require('web.test_utils');

QUnit.module('mail', {}, function () {
QUnit.module('Thread Window', {}, function () {
QUnit.module('Document Thread', {
    beforeEach: function () {
        var partnerID = 44;
        this.data = {
            'mail.message': {
                fields: {
                    body: {
                        string: "Contents",
                        type: 'html',
                    },
                    author_id: {
                        string: "Author",
                        type: 'many2one',
                        relation: 'res.partner',
                    },
                    channel_ids: {
                        string: "Channels",
                        type: 'many2many',
                        relation: 'mail.channel',
                    },
                    starred: {
                        string: "Starred",
                        type: 'boolean',
                    },
                    needaction: {
                      string: "Need Action",
                      type: 'boolean',
                    },
                    needaction_partner_ids: {
                        string: 'Needaction Partner IDs',
                        type: 'one2many',
                        relation: 'res.partner',
                    },
                    starred_partner_ids: {
                      string: "partner ids",
                      type: 'integer',
                    }
                },
                records: [{
                    id: 1,
                    author_id: [partnerID, 'Me'],
                    body: '<p>Some Message on a document</p>',
                    channel_ids: [],
                    model: 'some.res.model',
                    record_name: "Some Record",
                    res_id: 1,
                }, {
                    author_id: [2, "Demo"],
                    body: "<p>*MessageOnDocument*</p>",
                    id: 2,
                    model: 'some.res.model',
                    needaction: true,
                    needaction_partner_ids: [partnerID],
                    record_name: "Some Record",
                    res_id: 1,
                }],
            },
            'some.res.model': {
                fields: {
                    message_ids: {string: 'Messages', type: 'one2many'},
                },
                records: [{
                    id: 1,
                    message_ids: [1, 2],
                }],
            },
            initMessaging: {
                channel_slots: {
                    channel_channel: [],
                },
            },
        };
        this.session = {
            partner_id: partnerID, // so that needaction messages are treated as needactions
        };
        this.services = mailTestUtils.getMailServices();
    },
});

QUnit.test('open a document thread in a thread window', async function (assert) {
    assert.expect(6);

    var messagingMenu = new MessagingMenu();
    testUtils.mock.addMockEnvironment(messagingMenu, {
        services: this.services,
        data: this.data,
        session: this.session,
        mockRPC: function (route, args) {
            if (args.method === 'read') {
                assert.deepEqual(args.args, [[1], ['message_ids']],
                    "should read the message_ids on the document");
            }
            if (args.method === 'message_format') {
                assert.deepEqual(args.args[0], [1],
                    "should only fetch the unknown message");
            }
            return this._super.apply(this, arguments);
        },
    });
    await messagingMenu.appendTo($('#qunit-fixture'));

    // toggle the messaging menu and open the documentThread
    await testUtils.dom.click(messagingMenu.$('.dropdown-toggle'));
    assert.containsOnce(messagingMenu, '.o_mail_preview',
        "should display one preview");
    await testUtils.dom.click(messagingMenu.$('.o_mail_preview'));

    assert.strictEqual($('.o_thread_window').length, 1,
        "should have open the DocumentThread in a thread window");
    assert.strictEqual($('.o_thread_window .o_thread_message').length, 2,
        "should have fetched the history of the documentThread");
    assert.strictEqual($('.o_thread_window_title').text().trim(), 'Some Record',
        "should display the display_name of the record in the header");

    messagingMenu.destroy();
});

QUnit.test('expand a document thread window', async function (assert) {
    assert.expect(4);

    var messagingMenu = new MessagingMenu();
    testUtils.mock.addMockEnvironment(messagingMenu, {
        services: this.services,
        data: this.data,
        session: this.session,
        intercepts: {
            do_action: function (ev) {
                assert.deepEqual(ev.data.action, {
                    res_id: 1,
                    res_model: 'some.res.model',
                    type: 'ir.actions.act_window',
                    views: [[false, 'form']],
                }, "should open the document in form view");
            },
        },
    });
    await messagingMenu.appendTo($('#qunit-fixture'));

    // toggle the messaging menu and open the documentThread
    await testUtils.dom.click(messagingMenu.$('.dropdown-toggle'));
    assert.containsOnce(messagingMenu, '.o_mail_preview',
        "should display one preview");
    await testUtils.dom.click(messagingMenu.$('.o_mail_preview'));
    assert.strictEqual($('.o_thread_window').length, 1,
        "should have open the DocumentThread in a thread window");

    assert.hasAttrValue($('.o_thread_window .o_thread_window_expand'), 'title',
        'Open document', "button should have correct title");

    // click to expand
    await testUtils.dom.click($('.o_thread_window .o_thread_window_expand'));

    messagingMenu.destroy();
});

QUnit.test('post messages in a document thread window', async function (assert) {
    assert.expect(8);

    var newMessageBody = 'Some message';
    var newMessage = {
        id: 6783,
        author_id: [this.session.partner_id, 'Me'],
        body: newMessageBody,
        channel_ids: [],
        model: 'some.res.model',
        record_name: "Some Record",
        res_id: 1,
    };
    var messagingMenu = new MessagingMenu();
    testUtils.mock.addMockEnvironment(messagingMenu, {
        services: this.services,
        data: this.data,
        session: this.session,
        mockRPC: function (route, args) {
            if (args.method === 'message_post') {
                assert.strictEqual(args.model, 'some.res.model',
                    "should post the message on the correct model");
                assert.deepEqual(args.args, [1],
                    "should post the message on the correct record");
                assert.strictEqual(args.kwargs.body, newMessageBody,
                    "should post correct message");

                // add the message to the fake DB
                this.data['mail.message'].records.push(newMessage);
                this.data['some.res.model'].records[0].message_ids.push(6783);
                return Promise.resolve(6783);
            }
            return this._super.apply(this, arguments);
        },
    });
    testUtils.mock.intercept(messagingMenu, 'call_service', function (ev) {
        if (ev.data.service === 'local_storage' && ev.data.method === 'setItem' &&
            ev.data.args[0] === 'mail.document_threads_last_message') {
            assert.deepEqual(ev.data.args[1].messageData, newMessage,
                "should write sent message in local storage, to share info with other tabs");
        }
    }, true);
    await messagingMenu.appendTo($('#qunit-fixture'));

    // toggle the messaging menu and open the documentThread
    await testUtils.dom.click(messagingMenu.$('.dropdown-toggle'));
    assert.containsOnce(messagingMenu, '.o_mail_preview',
        "should display one preview");
    await testUtils.dom.click(messagingMenu.$('.o_mail_preview'));
    assert.strictEqual($('.o_thread_window').length, 1,
        "should have open the DocumentThread in a thread window");
    assert.strictEqual($('.o_thread_window .o_thread_message').length, 2,
        "should display 2 messages in the thread window");

    // post a message
    await testUtils.fields.editAndTrigger($('.o_thread_window .o_composer_text_field'), newMessageBody,
        [$.Event('keydown', {which: $.ui.keyCode.ENTER})]);
    assert.strictEqual($('.o_thread_window .o_thread_message').length, 3,
        "should display 3 messages in the thread window");

    messagingMenu.destroy();
});

QUnit.test('open, fold, unfold and close a document thread window', async function (assert) {
    assert.expect(24);
    var messagingMenu = new MessagingMenu();
    testUtils.mock.addMockEnvironment(messagingMenu, {
        services: this.services,
        data: this.data,
        session: this.session,
    });
    await testUtils.nextTick();
    testUtils.mock.intercept(messagingMenu, 'call_service', function (ev) {
        if (ev.data.service === 'local_storage' && ev.data.method === 'setItem') {
            const key = ev.data.args[0];
            const state = ev.data.args[1].state;
            assert.strictEqual(key, 'mail.document_threads_state/some.res.model_1');
            assert.ok(state);
            assert.ok(state.name);
            assert.ok(state.windowState);
            assert.step(`${key}: { name: "${state.name}", windowState: '${state.windowState}' }`);
        }
    }, true);
    await messagingMenu.appendTo($('#qunit-fixture'));

    // toggle the messaging menu and open the documentThread
    await testUtils.dom.click(messagingMenu.$('.dropdown-toggle'));
    assert.containsOnce(messagingMenu, '.o_mail_preview',
        "should display one preview");
    await testUtils.dom.click(messagingMenu.$('.o_mail_preview'));
    assert.strictEqual($('.o_thread_window').length, 1,
        "should have open the DocumentThread in a thread window");
    assert.strictEqual($('.o_thread_window .o_thread_message').length, 2,
        "should display 2 messages in the thread window");

    // fold and unfold thread window
    await testUtils.dom.click($('.o_thread_window .o_thread_window_title'));
    await testUtils.nextTick();
    await testUtils.dom.click($('.o_thread_window .o_thread_window_title'));
    await testUtils.nextTick();

    // close thread window
    await testUtils.dom.click($('.o_thread_window .o_thread_window_close'));
    await testUtils.nextTick();

    assert.verifySteps([
        `mail.document_threads_state/some.res.model_1: { name: "Some Record", windowState: 'open' }`,
        `mail.document_threads_state/some.res.model_1: { name: "Some Record", windowState: 'folded' }`,
        `mail.document_threads_state/some.res.model_1: { name: "Some Record", windowState: 'open' }`,
        `mail.document_threads_state/some.res.model_1: { name: "Some Record", windowState: 'closed' }`,
    ]);

    messagingMenu.destroy();
});

QUnit.test('do not open thread window on fetch message failure', async function (assert) {
    // this may happen when the user receives a notification from a document
    // that he does not have access rights at the moment.
    assert.expect(4);

    var messagingMenu = new MessagingMenu();
    testUtils.addMockEnvironment(messagingMenu, {
        services: this.services,
        data: this.data,
        session: this.session,
        mockRPC: function (route, args) {
            if (args.method === 'read' && args.model === 'some.res.model' && args.args[0][0] === 1) {
                assert.step('some.res.model/1/read');
                return Promise.reject(); // simulate failure
            }
            return this._super.apply(this, arguments);
        },
    });
    await messagingMenu.appendTo($('#qunit-fixture'));

    await testUtils.dom.click(messagingMenu.$('.dropdown-toggle'));
    assert.containsOnce(messagingMenu, '.o_mail_preview');

    await testUtils.dom.click(messagingMenu.$('.o_mail_preview'));
    assert.verifySteps(['some.res.model/1/read']);
    assert.strictEqual($('.o_thread_window').length, 0,
        "should not have open the DocumentThread in a thread window on fetch messages failure");

    messagingMenu.destroy();
});

});
});
});
