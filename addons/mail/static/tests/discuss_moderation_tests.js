odoo.define('mail.discuss_moderation_tests', function (require) {
"use strict";

var Thread = require('mail.model.Thread');
var mailTestUtils = require('mail.testUtils');

var createDiscuss = mailTestUtils.createDiscuss;

QUnit.module('mail', {}, function () {
QUnit.module('Discuss (Moderation)', {
    beforeEach: function () {
        // patch _.debounce and _.throttle to be fast and synchronous
        this.underscoreDebounce = _.debounce;
        this.underscoreThrottle = _.throttle;
        _.debounce = _.identity;
        _.throttle = _.identity;

        this.data = {
            'mail.message': {
                fields: {
                    body: {
                        string: "Contents",
                        type: 'html',
                    },
                    author_id: {
                        string: "Author",
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
                    starred_partner_ids: {
                        string: "partner ids",
                        type: 'integer',
                    },
                    model: {
                        string: "Related Document model",
                        type: 'char',
                    },
                    res_id: {
                        string: "Related Document ID",
                        type: 'integer',
                    },
                    need_moderation: {
                        string: "Need moderation",
                        type: 'boolean',
                    },
                    moderation_status: {
                        string: "Moderation Status",
                        type: 'integer',
                        selection: [
                            ['pending_moderation', 'Pending Moderation'],
                            ['accepted', 'Accepted'],
                            ['rejected', 'Rejected']
                        ],
                    },
                },
            },
        };
        this.services = mailTestUtils.getMailServices();
    },
    afterEach: function () {
        // unpatch _.debounce and _.throttle
        _.debounce = this.underscoreDebounce;
        _.throttle = this.underscoreThrottle;
    }
});

QUnit.test('moderator: display moderation box', function (assert) {
    assert.expect(1);
    var done = assert.async();

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [{
                id: 1,
                channel_type: "channel",
                name: "general",
                moderation: true,
            }],
        },
        is_moderator: true,
    };

    createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
    })
    .then(function (discuss) {
        var moderationBoxSelector = '.o_mail_discuss_item' +
                                    '[data-thread-id="mailbox_moderation"]';
        assert.strictEqual(discuss.$(moderationBoxSelector).length, 1,
            "there should be a moderation mailbox");
        discuss.destroy();
        done();
    });
});

QUnit.test('moderator: moderated channel with pending moderation message', function (assert) {
    assert.expect(33);
    var done = assert.async();

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [{
                id: 1,
                channel_type: "channel",
                name: "general",
                moderation: true,
            }],
        },
        is_moderator: true,
        moderation_counter: 1,
        moderation_channel_ids: [1],
    };
    this.data['mail.message'].records = [{
        author_id: [2, "Someone"],
        body: "<p>test</p>",
        id: 100,
        model: 'mail.channel',
        moderation_status: 'pending_moderation',
        need_moderation: true,
        res_id: 1,
    }];

    createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
    })
    .then(function (discuss) {
        var $moderationBox = discuss.$(
                                '.o_mail_discuss_item' +
                                '[data-thread-id="mailbox_moderation"]');
        var $mailboxCounter = $moderationBox.find('.o_mail_sidebar_needaction.badge');
        assert.strictEqual($mailboxCounter.length, 1,
            "there should be a counter next to the moderation mailbox in the sidebar");
        assert.strictEqual($mailboxCounter.text().trim(), "1",
            "the mailbox counter of the moderation mailbox should display '1'");

        // 1. go to moderation mailbox
        $moderationBox.click();
        var $message = discuss.$('.o_thread_message');
        // check message
        assert.strictEqual($message.length, 1,
            "there should be one message in the moderation box");
        assert.strictEqual($message.data('message-id'), 100,
            "this message pending moderation should have correct ID");
        assert.strictEqual($message.find('a[data-oe-id="1"]').text(), "#general",
            "the message pending moderation should have correct origin as its linked document");
        assert.strictEqual($message.find('.moderation_checkbox').length, 1,
            "there should be a moderation checkbox next to the message");
        assert.notOk($message.find('.moderation_checkbox').prop('checked'), false,
            "the moderation checkbox should be unchecked by default");
        // check moderation actions next to message
        assert.strictEqual(discuss.$('.o_thread_message_moderation').length, 5,
            "there should be 5 contextual moderation decisions next to the message");
        assert.strictEqual(discuss.$('.o_thread_message_moderation[data-decision="accept"]').length, 1,
            "there should be a contextual moderation decision to accept the message");
        assert.strictEqual(discuss.$('.o_thread_message_moderation[data-decision="reject"]').length, 1,
            "there should be a contextual moderation decision to reject the message");
        assert.strictEqual(discuss.$('.o_thread_message_moderation[data-decision="discard"]').length, 1,
            "there should be a contextual moderation decision to discard the message");
        assert.strictEqual(discuss.$('.o_thread_message_moderation[data-decision="allow"]').length, 1,
            "there should be a contextual moderation decision to allow the user of the message)");
        assert.strictEqual(discuss.$('.o_thread_message_moderation[data-decision="ban"]').length, 1,
            "there should be a contextual moderation decision to ban the user of the message");

        // check select all (enabled) / unselect all (disabled) buttons
        assert.strictEqual($('.o_mail_discuss_button_select_all').length, 1,
            "there should be a 'Select All' button in the control panel");
        assert.notOk($('.o_mail_discuss_button_select_all').hasClass('disabled'),
            "the 'Select All' button should not be disabled");
        assert.strictEqual($('.o_mail_discuss_button_unselect_all').length, 1,
            "there should be a 'Unselect All' button in the control panel");
        assert.ok($('.o_mail_discuss_button_unselect_all').hasClass('disabled'),
            "the 'Unselect All' button should be disabled");
        // check moderate all buttons (invisible)
        var moderateAllSelector = '.o_mail_discuss_button_moderate_all';
        assert.strictEqual($(moderateAllSelector).length, 3,
            "there should be 3 buttons to moderate selected messages in the control panel");
        assert.strictEqual($(moderateAllSelector + '[data-decision="accept"]').length, 1,
            "there should one moderate button to accept messages pending moderation");
        assert.ok($(moderateAllSelector + '[data-decision="accept"]').hasClass('d-none'),
            'the moderate button "Accept" should be invisible by default');
        assert.strictEqual($(moderateAllSelector + '[data-decision="reject"]').length, 1,
            "there should one moderate button to reject messages pending moderation");
        assert.ok($(moderateAllSelector + '[data-decision="reject"]').hasClass('d-none'),
            'the moderate button "Reject" should be invisible by default');
        assert.strictEqual($(moderateAllSelector + '[data-decision="discard"]').length, 1,
            "there should one moderate button to discard messages pending moderation");
        assert.ok($(moderateAllSelector + '[data-decision="discard"]').hasClass('d-none'),
            'the moderate button "Discard" should be invisible by default');

        // click on message moderation checkbox
        $message.find('.moderation_checkbox').click();
        assert.ok($message.find('.moderation_checkbox').prop('checked'),
            "the moderation checkbox should become checked after click");
        // check select all (disabled) / unselect all buttons (enabled)
        assert.ok($('.o_mail_discuss_button_select_all').hasClass('disabled'),
            "the 'Select All' button should be disabled");
        assert.notOk($('.o_mail_discuss_button_unselect_all').hasClass('disabled'),
            "the 'Unselect All' button should not be disabled");
        // check moderate all buttons updated (visible)
        assert.notOk($(moderateAllSelector + '[data-decision="accept"]').hasClass('d-none'),
            'the moderate button "Accept" should become visible');
        assert.notOk($(moderateAllSelector + '[data-decision="reject"]').hasClass('d-none'),
            'the moderate button "Reject" should become visible');
        assert.notOk($(moderateAllSelector + '[data-decision="discard"]').hasClass('d-none'),
            'the moderate button "Discard" should become visible');

        // 2. go to channel 'general'
        discuss.$('.o_mail_discuss_item[data-thread-id="1"]').click();
        $message = discuss.$('.o_thread_message');
        // check correct message
        assert.strictEqual($message.length, 1,
            "there should be one message in the general channel");
        assert.strictEqual($message.data('message-id'), 100,
            "this message should have correct ID");
        assert.notOk($message.find('.moderation_checkbox').prop('checked'),
            "the moderation checkbox should be unchecked by default");

        // don't check moderation actions visibility, since it is similar to moderation box.
        discuss.destroy();
        done();
    });
});

QUnit.test('moderator: accept pending moderation message', function (assert) {
    assert.expect(12);
    var done = assert.async();

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [{
                id: 1,
                channel_type: "channel",
                name: "general",
                moderation: true,
            }],
        },
        is_moderator: true,
        moderation_counter: 1,
        moderation_channel_ids: [1],
    };
    this.data['mail.message'].records = [{
        author_id: [2, "Someone"],
        body: "<p>test</p>",
        channel_ids: [],
        id: 100,
        model: 'mail.channel',
        moderation_status: 'pending_moderation',
        need_moderation: true,
        res_id: 1,
    }];

    createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        mockRPC: function (route, args) {
            if (args.method === 'moderate') {
                assert.step('moderate');
                var messageIDs = args.args[0];
                var decision = args.args[1];
                assert.strictEqual(messageIDs.length, 1, "should moderate one message");
                assert.strictEqual(messageIDs[0], 100, "should moderate message with ID 100");
                assert.strictEqual(decision, 'accept', "should accept the message");
            }
            return this._super.apply(this, arguments);
        },
    })
    .then(function (discuss) {
        // 1. go to moderation box
        var $moderationBox = discuss.$(
                                '.o_mail_discuss_item' +
                                '[data-thread-id="mailbox_moderation"]');
        $moderationBox.click();
        // check there is a message to moderate
        var $message = discuss.$('.o_thread_message');
        assert.strictEqual($message.length, 1,
            "there should be one message in the moderation box");
        assert.strictEqual($message.data('message-id'), 100,
            "this message should have correct ID");
        assert.strictEqual($message.find('.moderation_checkbox').length, 1,
            "the message should have a moderation checkbox");
        // accept the message pending moderation
        discuss.$('.o_thread_message_moderation[data-decision="accept"]').click();
        assert.verifySteps(['moderate']);

        // stop the fadeout animation and immediately remove the element
        discuss.$('.o_thread_message').stop(false, true);
        assert.strictEqual(discuss.$('.o_thread_message').length, 0,
            "should now have no message displayed in moderation box");

        // 2. go to channel 'general'
        discuss.$('.o_mail_discuss_item[data-thread-id="1"]').click();
        $message = discuss.$('.o_thread_message');
        // check message is there and has no moderate checkbox
        assert.strictEqual($message.length, 1,
            "there should be one message in the general channel");
        assert.strictEqual($message.data('message-id'), 100,
            "this message should have correct ID");
        assert.strictEqual($message.find('.moderation_checkbox').length, 0,
            "the message should not have any moderation checkbox");

        discuss.destroy();
        done();
    });
});

QUnit.test('moderator: reject pending moderation message (reject with explanation)', function (assert) {
    assert.expect(21);
    var done = assert.async();

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [{
                id: 1,
                channel_type: "channel",
                name: "general",
                moderation: true,
            }],
        },
        is_moderator: true,
        moderation_counter: 1,
        moderation_channel_ids: [1],
    };
    this.data['mail.message'].records = [{
        author_id: [2, "Someone"],
        body: "<p>test</p>",
        channel_ids: [],
        id: 100,
        model: 'mail.channel',
        moderation_status: 'pending_moderation',
        need_moderation: true,
        res_id: 1,
    }];

    createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        mockRPC: function (route, args) {
            if (args.method === 'moderate') {
                assert.step('moderate');
                var messageIDs = args.args[0];
                var decision = args.args[1];
                var kwargs = args.kwargs;
                assert.strictEqual(messageIDs.length, 1, "should moderate one message");
                assert.strictEqual(messageIDs[0], 100, "should moderate message with ID 100");
                assert.strictEqual(decision, 'reject', "should reject the message");
                assert.strictEqual(kwargs.title, "Message Rejected",
                    "should have correct reject message title");
                assert.strictEqual(kwargs.comment, "Your message was rejected by moderator.",
                    "should have correct reject message body / comment");
            }
            return this._super.apply(this, arguments);
        },
    })
    .then(function (discuss) {
        // 1. go to moderation box
        var $moderationBox = discuss.$(
                                '.o_mail_discuss_item' +
                                '[data-thread-id="mailbox_moderation"]');
        $moderationBox.click();
        // check there is a message to moderate
        var $message = discuss.$('.o_thread_message');
        assert.strictEqual($message.length, 1,
            "there should be one message in the moderation box");
        assert.strictEqual($message.data('message-id'), 100,
            "this message should have correct ID");
        assert.strictEqual($message.find('.moderation_checkbox').length, 1,
            "the message should have a moderation checkbox");
        // reject the message pending moderation
        discuss.$('.o_thread_message_moderation[data-decision="reject"]').click();

        // check reject dialog prompt
        assert.strictEqual($('.modal-dialog').length, 1,
            "a dialog should be prompt to the moderator on click reject");
        assert.strictEqual($('.modal-title').text(), "Send explanation to author",
            "dialog should have correct title");
        var $messageTitle = $('.modal-body input[id="message_title"]');
        assert.strictEqual($messageTitle.length, 1,
            "should have a title of message for rejecting the message");
        assert.strictEqual($messageTitle.attr('placeholder'), "Subject",
            "message title for reject reason should have correct placeholder");
        assert.strictEqual($messageTitle.val(), "Message Rejected",
            "message title for reject reason should have correct default value");
        var $messageBody = $('.modal-body textarea[id="reject_message"]');
        assert.strictEqual($messageBody.length, 1,
            "should have a body of message for rejecting the message");
        assert.strictEqual($messageBody.attr('placeholder'), "Mail Body",
            "message body for reject reason should have correct placeholder");
        assert.strictEqual($messageBody.text(), "Your message was rejected by moderator.",
            "message body for reject reason should have correct default text content");
        assert.strictEqual($('.modal-footer button').text(), "Send",
            "should have a send button on the reject dialog");

        // send mesage
        $('.modal-footer button').click();
        assert.verifySteps(['moderate']);

        // // stop the fadeout animation and immediately remove the element
        discuss.$('.o_thread_message').stop(false, true);
        assert.strictEqual(discuss.$('.o_thread_message').length, 0,
            "should now have no message displayed in moderation box");

        // 2. go to channel 'general'
        discuss.$('.o_mail_discuss_item[data-thread-id="1"]').click();
        assert.strictEqual(discuss.$('.o_thread_message').length, 0,
            "should now have no message displayed in moderated channel");

        discuss.destroy();
        done();
    });
});

QUnit.test('moderator: discard pending moderation message (reject without explanation)', function (assert) {
    assert.expect(15);
    var done = assert.async();

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [{
                id: 1,
                channel_type: "channel",
                name: "general",
                moderation: true,
            }],
        },
        is_moderator: true,
        moderation_counter: 1,
        moderation_channel_ids: [1],
    };
    this.data['mail.message'].records = [{
        author_id: [2, "Someone"],
        body: "<p>test</p>",
        channel_ids: [],
        id: 100,
        model: 'mail.channel',
        moderation_status: 'pending_moderation',
        need_moderation: true,
        res_id: 1,
    }];

    createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        mockRPC: function (route, args) {
            if (args.method === 'moderate') {
                assert.step('moderate');
                var messageIDs = args.args[0];
                var decision = args.args[1];
                assert.strictEqual(messageIDs.length, 1, "should moderate one message");
                assert.strictEqual(messageIDs[0], 100, "should moderate message with ID 100");
                assert.strictEqual(decision, 'discard', "should discard the message");
            }
            return this._super.apply(this, arguments);
        },
    })
    .then(function (discuss) {
        // 1. go to moderation box
        var $moderationBox = discuss.$(
                                '.o_mail_discuss_item' +
                                '[data-thread-id="mailbox_moderation"]');
        $moderationBox.click();
        // check there is a message to moderate
        var $message = discuss.$('.o_thread_message');
        assert.strictEqual($message.length, 1,
            "there should be one message in the moderation box");
        assert.strictEqual($message.data('message-id'), 100,
            "this message should have correct ID");
        assert.strictEqual($message.find('.moderation_checkbox').length, 1,
            "the message should have a moderation checkbox");
        // discard the message pending moderation
        discuss.$('.o_thread_message_moderation[data-decision="discard"]').click();

        // check discard dialog prompt
        assert.strictEqual($('.modal-dialog').length, 1,
            "a dialog should be prompt to the moderator on click discard");
        assert.strictEqual($('.modal-body:first').text(),
            "You are going to discard 1 message. Do you confirm the action?",
            "should warn the user on discard action");
        assert.strictEqual($('.modal-footer button').length, 2,
            "should have two buttons in the footer of the dialog");
        assert.strictEqual($('.modal-footer button.btn-primary').text(), "Ok",
            "should have a confirm button in the dialog for discard");
        assert.strictEqual($('.modal-footer button.btn-secondary').text(), "Cancel",
            "should have a cancel button in the dialog for discard");

        // discard mesage
        $('.modal-footer button.btn-primary').click();
        assert.verifySteps(['moderate']);

        // stop the fadeout animation and immediately remove the element
        discuss.$('.o_thread_message').stop(false, true);
        assert.strictEqual(discuss.$('.o_thread_message').length, 0,
            "should now have no message displayed in moderation box");

        // 2. go to channel 'general'
        discuss.$('.o_mail_discuss_item[data-thread-id="1"]').click();
        assert.strictEqual(discuss.$('.o_thread_message').length, 0,
            "should now have no message displayed in moderated channel");

        discuss.destroy();
        done();
    });
});

QUnit.test('author: send message in moderated channel', function (assert) {
    assert.expect(4);
    var done = assert.async();

    var messagePostDef = $.Deferred();

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [{
                id: 1,
                channel_type: "channel",
                name: "general",
                moderation: true,
            }],
        },
    };

    var objectDiscuss;
    createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        mockRPC: function (route, args) {
            if (args.method === 'message_post') {
                var message = {
                    id: 100,
                    author_id: [2, 'Someone'],
                    body: args.kwargs.body,
                    message_type: args.kwargs.message_type,
                    model: 'mail.channel',
                    moderation_status: 'pending_moderation',
                    res_id: 1,
                };
                var metaData = [undefined, 'res.partner'];
                var notifData = {
                    type: 'author',
                    message: message,
                };
                var notification = [metaData, notifData];
                objectDiscuss.call('bus_service', 'trigger', 'notification', [notification]);

                messagePostDef.resolve();
                return $.when(message.id);
            }
            return this._super.apply(this, arguments);
        },
        session: {
            partner_id: 2,
        },
    })
    .then(function (discuss) {
        objectDiscuss = discuss;

        // go to channel 'general'
        discuss.$('.o_mail_discuss_item[data-thread-id="1"]').click();
        // post a message
        discuss.$('.o_composer_input textarea').first().val("some text");
        discuss.$('.o_composer_send button').click();

        messagePostDef
            .then(function () {

                var $message = discuss.$('.o_thread_message');
                assert.strictEqual($message.length, 1,
                    "should have a message in the thread");
                assert.strictEqual($message.data('message-id'), 100,
                    "message should have ID returned from 'message_post'");
                assert.strictEqual($message.find('.o_thread_author').text().trim(),
                    "Someone", "message should have correct author displayed name");
                assert.strictEqual(discuss.$('.o_thread_icons i.text-danger').text(),
                    "Pending moderation", "the message should be pending moderation");

                discuss.destroy();
                done();
            });
    });
});

QUnit.test('author: sent message accepted in moderated channel', function (assert) {
    assert.expect(8);
    var done = assert.async();

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [{
                id: 1,
                channel_type: "channel",
                name: "general",
                moderation: true,
            }],
        },
    };

    this.data['mail.message'].records = [{
        author_id: [2, "Someone"],
        body: "<p>test</p>",
        channel_ids: [],
        id: 100,
        model: 'mail.channel',
        moderation_status: 'pending_moderation',
        need_moderation: true,
        res_id: 1,
    }];

    createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        session: {
            partner_id: 2,
        },
    })
    .then(function (discuss) {

        // go to channel 'general'
        discuss.$('.o_mail_discuss_item[data-thread-id="1"]').click();
        // check message is pending
        var $message = discuss.$('.o_thread_message');
        assert.strictEqual($message.length, 1,
            "should have a message in the thread");
        assert.strictEqual($message.data('message-id'), 100,
            "message should have ID returned from 'message_post'");
        assert.strictEqual($message.find('.o_thread_author').text().trim(),
            "Someone", "message should have correct author displayed name");
        assert.strictEqual(discuss.$('.o_thread_icons i.text-danger').text(),
            "Pending moderation", "the message should be pending moderation");

        // simulate accepted message
        var dbName = undefined; // useless for tests
        var messageData = {
            author_id: [2, "Someone"],
            body: "<p>test</p>",
            channel_ids: [],
            id: 100,
            model: 'mail.channel',
            moderation_status: 'accepted'
        };
        var metaData = [dbName, 'mail.channel'];
        var notification = [metaData, messageData];
        discuss.call('bus_service', 'trigger', 'notification', [notification]);

        // check message is accepted
        $message = discuss.$('.o_thread_message');
        assert.strictEqual($message.length, 1,
            "should still have a message in the thread");
        assert.strictEqual($message.data('message-id'), 100,
            "message should still have ID returned from 'message_post'");
        assert.strictEqual($message.find('.o_thread_author').text().trim(),
            "Someone", "message should still have correct author displayed name");
        assert.strictEqual(discuss.$('.o_thread_icons i.text-danger').length, 0,
            "the message should not be in pending moderation anymore");

        discuss.destroy();
        done();
    });
});

QUnit.test('author: sent message rejected in moderated channel', function (assert) {
    assert.expect(5);
    var done = assert.async();

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [{
                id: 1,
                channel_type: "channel",
                name: "general",
                moderation: true,
            }],
        },
    };

    this.data['mail.message'].records = [{
        author_id: [2, "Someone"],
        body: "<p>test</p>",
        channel_ids: [],
        id: 100,
        model: 'mail.channel',
        moderation_status: 'pending_moderation',
        need_moderation: true,
        res_id: 1,
    }];

    createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        session: {
            partner_id: 2,
        },
    })
    .then(function (discuss) {

        // go to channel 'general'
        discuss.$('.o_mail_discuss_item[data-thread-id="1"]').click();
        // check message is pending
        var $message = discuss.$('.o_thread_message');
        assert.strictEqual($message.length, 1,
            "should have a message in the thread");
        assert.strictEqual($message.data('message-id'), 100,
            "message should have ID returned from 'message_post'");
        assert.strictEqual($message.find('.o_thread_author').text().trim(),
            "Someone", "message should have correct author displayed name");
        assert.strictEqual(discuss.$('.o_thread_icons i.text-danger').text(),
            "Pending moderation", "the message should be pending moderation");

        // simulate reject from moderator
        var dbName = undefined; // useless for tests
        var notifData = {
            type: 'deletion',
            message_ids: [100],
        };
        var metaData = [dbName, 'res.partner'];
        var notification = [metaData, notifData];
        discuss.call('bus_service', 'trigger', 'notification', [notification]);

        // // check no message
        assert.strictEqual(discuss.$('.o_thread_message').length, 0,
            "message should be removed from channel after reject");

        discuss.destroy();
        done();
    });
});

QUnit.test('no crash when load-more fetching "accepted" message twice', function (assert) {
    // This tests requires discuss not loading more messages due to having less
    // messages to fetch than available height. This justifies we simply do not
    // patch FETCH_LIMIT to 1, as it would detect that more messages could fit
    // the empty space (it behaviour is linked to "auto load more").
    var done = assert.async();
    assert.expect(2);

    var FETCH_LIMIT = Thread.prototype._FETCH_LIMIT;
    // FETCH LIMIT + 30 should be enough to cover the whole available space in
    // the thread of discuss app.
    var messageData = [];
    _.each(_.range(1, FETCH_LIMIT+31), function (num) {
        messageData.push({
                id: num,
                body: "<p>test" + num + "</p>",
                author_id: [100, "Someone"],
                channel_ids: [1],
                model: 'mail.channel',
                res_id: 1,
                moderation_status: 'accepted',
            }
        );
    });

    this.data['mail.message'].records = messageData;

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [{
                id: 1,
                channel_type: "channel",
                name: "general",
            }],
        },
    };
    var count = 0;

    createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        session: { partner_id: 3 },
        mockRPC: function (route, args) {
            if (args.method === 'message_fetch') {
                count++;
                if (count === 1) {
                    // inbox message_fetch
                    return $.when([]);
                }
                // general message_fetch
                return $.when(messageData);
            }
            return this._super.apply(this, arguments);
        },
    })
    .then(function (discuss) {
        var $general = discuss.$('.o_mail_discuss_sidebar')
                        .find('.o_mail_discuss_item[data-thread-id=1]');
        assert.strictEqual($general.length, 1,
            "should have the channel item with id 1");
        assert.strictEqual($general.attr('title'), 'general',
            "should have the title 'general'");

        // click on general
        $general.click();

        // simulate search
        discuss.trigger_up('search', {
            domains: [['author_id', '=', 100]],
        });

        discuss.destroy();
        done();
    });
});

});
});
