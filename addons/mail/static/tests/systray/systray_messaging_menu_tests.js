odoo.define('mail.systray.MessagingMenuTests', function (require) {
"use strict";

var DocumentThread = require('mail.model.DocumentThread');
var MessagingMenu = require('mail.systray.MessagingMenu');
var mailTestUtils = require('mail.testUtils');

var testUtils = require('web.test_utils');

QUnit.module('mail', {}, function () {
QUnit.module('MessagingMenu', {
    beforeEach: function () {
        // patch _.debounce and _.throttle to be fast and synchronous
        this.underscoreDebounce = _.debounce;
        this.underscoreThrottle = _.throttle;
        _.debounce = _.identity;
        _.throttle = _.identity;

        this.data = {
            'mail.channel': {
                fields: {
                    name: {
                        string: "Name",
                        type: "char",
                        required: true,
                    },
                    channel_type: {
                        string: "Channel Type",
                        type: "selection",
                    },
                    channel_message_ids: {
                        string: "Messages",
                        type: "many2many",
                        relation: 'mail.message'
                    },
                },
                records: [{
                    id: 1,
                    name: "general",
                    channel_type: "channel",
                    channel_message_ids: [1],
                }],
            },
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
                        string: "Needaction partner IDs",
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
                    author_id: ['1', 'Me'],
                    body: '<p>test</p>',
                    channel_ids: [1],
                }],
            },
            initMessaging: {
                channel_slots: {
                    channel_channel: [{
                        id: 1,
                        channel_type: "channel",
                        name: "general",
                    }],
                },
            },
        };
        this.services = mailTestUtils.getMailServices();
        this.MailService = this.services.mail_service;
        this.MailService.prototype.IS_STATIC_PREVIEW_ENABLED = false;
    },
    afterEach: function () {
        this.MailService.prototype.IS_STATIC_PREVIEW_ENABLED = true;
        // unpatch _.debounce and _.throttle
        _.debounce = this.underscoreDebounce;
        _.throttle = this.underscoreThrottle;
    }
});

QUnit.test('messaging menu widget: menu with no records', function (assert) {
    assert.expect(1);

    var messagingMenu = new MessagingMenu();
    testUtils.addMockEnvironment(messagingMenu, {
            services: this.services,
            mockRPC: function (route, args) {
                if (args.method === 'message_fetch') {
                    return $.when([]);
                }
                return this._super.apply(this, arguments);
            }
        });
    messagingMenu.appendTo($('#qunit-fixture'));
    messagingMenu.$('.dropdown-toggle').click();
    assert.ok(messagingMenu.$('.o_no_activity').hasClass('o_no_activity'), "should not have instance of widget");
    messagingMenu.destroy();
});

QUnit.test('messaging menu widget: messaging menu with 1 record', function (assert) {
    assert.expect(3);
    var messagingMenu = new MessagingMenu();
    testUtils.addMockEnvironment(messagingMenu, {
        services: this.services,
        data: this.data,
    });
    messagingMenu.appendTo($('#qunit-fixture'));

    messagingMenu.$('.dropdown-toggle').click();

    assert.strictEqual(messagingMenu.$('.o_mail_preview').length, 1,
        "should display a preview");
    assert.strictEqual(messagingMenu.$('.o_preview_name').text().trim(), "general",
        "should display correct name of channel in preview");

    // remove any space-character inside text
    var lastMessagePreviewText =
        messagingMenu.$('.o_last_message_preview').text().replace(/\s/g, "");
    assert.strictEqual(lastMessagePreviewText,
        "Me:test",
        "should display correct last message preview in channel preview");

    messagingMenu.destroy();
});

QUnit.test('messaging menu widget: no crash when clicking on inbox notification not associated to a document', function (assert) {
    assert.expect(3);

    var messagingMenu = new MessagingMenu();
    testUtils.addMockEnvironment(messagingMenu, {
        services: this.services,
        data: this.data,
        session: {
            partner_id: 1,
        },
        intercepts: {
            /**
             * Simulate action 'mail.mail_channel_action_client_chat'
             * successfully performed.
             *
             * @param {OdooEvent} ev
             * @param {function} ev.data.on_success called when success action performed
             */
            do_action: function (ev) {
                ev.data.on_success();
            },
        },
    });
    messagingMenu.appendTo($('#qunit-fixture'));

    // Simulate received needaction message without associated document,
    // so that we have a message in inbox without a model and a resID
    var message = {
        id: 2,
        author_id: [1, "Me"],
        body: '<p>test</p>',
        channel_ids: [],
        needaction_partner_ids: [1],
    };
    var notifications = [
        [['myDB', 'ir.needaction'], message]
    ];
    messagingMenu.call('bus_service', 'trigger', 'notification', notifications);

    // Open messaging menu
    messagingMenu.$('.dropdown-toggle').click();

    var $firstChannelPreview =
        messagingMenu.$('.o_mail_preview').first();

    assert.strictEqual($firstChannelPreview.length, 1,
        "should have at least one channel preview");
    assert.strictEqual($firstChannelPreview.data('preview-id'),
        'mailbox_inbox',
        "should be a preview from channel inbox");
    try {
        $firstChannelPreview.click();
        assert.ok(true, "should not have crashed when clicking on needaction preview message");
    } finally {
        messagingMenu.destroy();
    }
});

QUnit.test("messaging menu widget: mark as read on thread preview", function ( assert ) {
    assert.expect(8);

    testUtils.patch(DocumentThread, {
            markAsRead: function () {
                if (
                    this.getDocumentModel() === 'crm.lead' &&
                    this.getDocumentID() === 126
                ) {
                    assert.step('markedAsRead');
                }
            },
        });

    this.data['mail.message'].records = [{
        id: 10,
        channel_ids: ['mailbox_inbox'],
        res_id: 126,
        needaction: true,
        module_icon: "/crm/static/description/icon.png",
        date: "2018-04-05 06:37:26",
        subject: "Re: Interest in your Graphic Design Project",
        model: "crm.lead",
        body: "<span>Testing Messaging</span>"
    }];

    var messagingMenu = new MessagingMenu();
    testUtils.addMockEnvironment(messagingMenu, {
        services: this.services,
        data: this.data,
    });

    messagingMenu.appendTo($('#qunit-fixture'));
    messagingMenu.$('.dropdown-toggle').click();
    assert.ok(messagingMenu.$el.hasClass('o_mail_systray_item'),
        'should be the instance of widget');
    assert.ok(messagingMenu.$el.hasClass('show'),
        'MessagingMenu should be open');

    var $preview = messagingMenu.$('.o_mail_preview.o_preview_unread');
    assert.strictEqual($preview.length, 1,
        "should have one unread preview");
    assert.strictEqual($preview.data('document-model'), 'crm.lead',
        "should preview be linked to correct document model");
    assert.strictEqual($preview.data('document-id'), 126,
        "should preview be linked to correct document ID");
    assert.strictEqual(messagingMenu.$('.o_mail_preview_mark_as_read').length, 1,
        "should have mark as read icon next to preview");

    messagingMenu.$(".o_mail_preview_mark_as_read").click();

    assert.verifySteps(['markedAsRead'],
        "the document thread should be marked as read");

    testUtils.unpatch(DocumentThread);
    messagingMenu.destroy();
});

QUnit.test('needaction messages in channels should appear, in addition to channel preview', function (assert) {
    // Let's suppose a channel whose before-last message (msg1) is a needaction,
    // but not the last message (msg2). In that case, the systray messaging
    // menu should display the needaction message msg1 in the preview, and the
    // channel preview with the msg2.
    assert.expect(3);

    // simulate a needaction (mention) message in channel 'general'
    var partnerID = 44;
    var needactionMessage = {
        author_id: [1, "Demo"],
        body: "<p>@Administrator: ping</p>",
        channel_ids: [1],
        id: 3,
        model: 'mail.channel',
        needaction: true,
        needaction_partner_ids: [partnerID],
        record_name: 'general',
        res_id: 1,
    };
    var lastMessage = {
        author_id: [2, "Other"],
        body: "<p>last message content</p>",
        channel_ids: [1],
        id: 4,
        model: 'mail.channel',
        record_name: 'general',
        res_id: 1,
    };
    this.data['mail.message'].records = [needactionMessage, lastMessage];

    var messagingMenu = new MessagingMenu();
    testUtils.addMockEnvironment(messagingMenu, {
        services: this.services,
        data: this.data,
        session: {
            partner_id: partnerID,
        },
    });
    messagingMenu.appendTo($('#qunit-fixture'));

    messagingMenu.$('.dropdown-toggle').click();

    assert.strictEqual(messagingMenu.$('.o_mail_preview').length, 2,
        "should display two previews");
    var $preview1 = messagingMenu.$('.o_mail_preview').eq(0);
    var $preview2 = messagingMenu.$('.o_mail_preview').eq(1);

    assert.strictEqual($preview1.find('.o_last_message_preview').text().replace(/\s/g, ""),
        "Demo:@Administrator:ping",
        "1st preview (needaction preview) should display needaction message");
    assert.strictEqual($preview2.find('.o_last_message_preview').text().replace(/\s/g, ""),
        "Other:lastmessagecontent",
        "2nd preview (channel preview) should display last message preview");

    messagingMenu.destroy();
});

QUnit.test('preview of message on a document', function (assert) {
    assert.expect(3);

    var partnerID = 44;
    var needactionMessage = {
        author_id: [1, "Demo"],
        body: "<p>*MessageOnDocument*</p>",
        id: 689,
        model: 'some.res.model',
        needaction: true,
        needaction_partner_ids: [partnerID],
        record_name: "Some Record",
        res_id: 1,
    };
    this.data['some.res.model'] = {
        fields: {
            message_ids: {string: 'Messages', type: 'one2many'},
        },
        records: [{
            id: 1,
            message_ids: [689],
        }],
    };
    this.data['mail.message'].records.push(needactionMessage);

    var messagingMenu = new MessagingMenu();
    testUtils.addMockEnvironment(messagingMenu, {
        services: this.services,
        data: this.data,
        session: {
            partner_id: partnerID,
        },
    });
    messagingMenu.appendTo($('#qunit-fixture'));

    messagingMenu.$('.dropdown-toggle').click();

    assert.strictEqual(messagingMenu.$('.o_mail_preview').length, 2,
        "should display two channel previews");
    assert.ok(messagingMenu.$('.o_mail_preview:first').hasClass('o_preview_unread'),
        "document thread preview should be marked as unread");
    assert.strictEqual(messagingMenu.$('.o_preview_unread .o_last_message_preview').text().replace(/\s/g, ''),
        "Demo:*MessageOnDocument*", "should correctly display the preview");

    messagingMenu.destroy();
});

QUnit.test('update messaging preview on receiving a new message in channel preview', function (assert) {
    assert.expect(8);

    var messagingMenu = new MessagingMenu();
    testUtils.addMockEnvironment(messagingMenu, {
        services: this.services,
        data: this.data,
    });
    messagingMenu.appendTo($('#qunit-fixture'));

    messagingMenu.$('.dropdown-toggle').click();

    assert.strictEqual(messagingMenu.$('.o_mail_preview').length, 1,
        "should display a single channel preview");
    assert.strictEqual(messagingMenu.$('.o_preview_name').text().trim(), "general",
        "should display channel preview of 'general' channel");
    assert.strictEqual(messagingMenu.$('.o_preview_counter').text().trim(), "",
        "should have unread counter of 0 for 'general' channel (no unread messages)");
    // remove any space-character inside text
    var lastMessagePreviewText =
        messagingMenu.$('.o_last_message_preview').text().replace(/\s/g, "");
    assert.strictEqual(lastMessagePreviewText,
        "Me:test",
        "should display author name and inline body of currently last message in the channel");

    // simulate receiving a new message on the channel 'general' (id 1)
    var data = {
        id: 100,
        author_id: [42, "Someone"],
        body: "<p>A new message content</p>",
        channel_ids: [1],
    };
    var notification = [[false, 'mail.channel', 1], data];
    messagingMenu.call('bus_service', 'trigger', 'notification', [notification]);

    assert.strictEqual(messagingMenu.$('.o_mail_preview').length, 1,
        "should still display a single channel preview");
    assert.strictEqual(messagingMenu.$('.o_preview_name').text().trim(), "general",
        "should still display channel preview of 'general' channel");
    assert.strictEqual(messagingMenu.$('.o_preview_counter').text().trim(), "(1)",
        "should have incremented unread counter of 'general' channel");
    // remove any space-character inside text
    lastMessagePreviewText =
        messagingMenu.$('.o_last_message_preview').text().replace(/\s/g, "");
    assert.strictEqual(lastMessagePreviewText,
        "Someone:Anewmessagecontent",
        "should display author name and inline body of newly received message");

    messagingMenu.destroy();
});

});
});
