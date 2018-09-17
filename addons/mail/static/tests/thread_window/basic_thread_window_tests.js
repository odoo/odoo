odoo.define('mail.basicThreadWindowTests', function (require) {
"use strict";

var mailTestUtils = require('mail.testUtils');

var framework = require('web.framework');
var testUtils = require('web.test_utils');
var Widget = require('web.Widget');

QUnit.module('mail', {}, function () {
QUnit.module('Thread Window', {}, function () {
QUnit.module('Basic', {
    beforeEach: function () {
        var self = this;

        // define channel to link to chat window
        this.data = {
            'mail.message': {
                fields: {},
                records: [],
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
        this.ORIGINAL_THREAD_WINDOW_APPENDTO = this.services.mail_service.prototype.THREAD_WINDOW_APPENDTO;

        this.createParent = function (params) {
            var widget = new Widget();

            // in non-debug mode, append thread windows in qunit-fixture
            // note that it does not hide thread window because it uses fixed
            // position, and qunit-fixture uses absolute...
            if (params.debug) {
                self.services.mail_service.prototype.THREAD_WINDOW_APPENDTO = 'body';
            } else {
                self.services.mail_service.prototype.THREAD_WINDOW_APPENDTO = '#qunit-fixture';
            }

            testUtils.addMockEnvironment(widget, params);
            return widget;
        };
    },
    afterEach: function () {
        // reset thread window append to body
        this.services.mail_service.prototype.THREAD_WINDOW_APPENDTO = 'body';
    },
});

QUnit.test('basic rendering thread window', function (assert) {
    assert.expect(10);

    var parent = this.createParent({
        data: this.data,
        services: this.services,
    });

    // detach channel 1, so that it opens corresponding thread window.
    parent.call('mail_service', 'getChannel', 1).detach();

    var $threadWindow = $('.o_thread_window');
    assert.strictEqual($threadWindow.length, 1,
        "thread window should be open");
    assert.strictEqual($threadWindow.data('thread-id'), 1,
        "thread window should be related to thread ID 1");

    var $header = $threadWindow.find('.o_thread_window_header');
    assert.strictEqual($header.length, 1,
        "thread window should have a header");

    var $title = $header.find('.o_thread_window_title');
    assert.strictEqual($title.length, 1,
        "thread window should have a title in the header");
    assert.strictEqual($title.text().trim(), "#general",
        "should have the title of the general channel");

    var $buttons = $header.find('.o_thread_window_buttons');
    assert.strictEqual($buttons.length, 1,
        "should have buttons in the header of the thread window");
    assert.strictEqual($buttons.find('.o_thread_window_expand').length, 1,
        "should have a button to expand the thread window");
    assert.strictEqual($buttons.find('.o_thread_window_close').length, 1,
        "should have a button to close the thread window");

    assert.strictEqual($threadWindow.find('.o_mail_thread').length, 1,
        "should display the content of the general channel in the thread window");
    assert.strictEqual($threadWindow.find('.o_thread_composer').length, 1,
        "should display a composer in the thread window");

    parent.destroy();
});

QUnit.test('close thread window using ESCAPE key', function (assert) {
    assert.expect(5);

    var parent = this.createParent({
        data: this.data,
        services: this.services,
        mockRPC: function (route, args) {
            if (args.method === 'channel_fold') {
                assert.ok(true, "should call channel_fold");
                return $.when();
            }
            return this._super.apply(this, arguments);
        },
    });

    // get channel instance to link to thread window
    var channel = parent.call('mail_service', 'getChannel', 1);
    assert.ok(channel, "there should exist a channel locally with ID 1");

    channel.detach();
    assert.strictEqual($('.o_thread_window').length, 1,
        "there should be a thread window that is opened");

    // focus on the thread window and press ESCAPE
    $('.o_thread_window .o_composer_text_field').click();
    assert.strictEqual(document.activeElement,
        $('.o_thread_window .o_composer_text_field')[0],
        "thread window's input should now be focused");

    var upKeyEvent = $.Event( "keyup", { which: 27 });
    $('.o_thread_window .o_composer_text_field').trigger(upKeyEvent);

    assert.strictEqual($('.o_thread_window').length, 0,
        "the thread window should be closed");

    parent.destroy();
});

QUnit.test('thread window\'s input can still be focused when the UI is blocked', function (assert) {
    assert.expect(2);

    var parent = this.createParent({
        data: this.data,
        services: this.services,
    });

    var $dom = $('#qunit-fixture');

    // get channel instance to link to thread window
    var channel = parent.call('mail_service', 'getChannel', 1);
    channel.detach();

    var $input = $('<input/>', {type: 'text'}).appendTo($dom);
    $input.focus().click();
    assert.strictEqual(document.activeElement, $input[0],
        "fake input should be focused");

    framework.blockUI();
    // cannot force focus here otherwise the test
    // makes no sense, this test is just about
    // making sure that the code which forces the
    // focus on click is not removed
    $('.o_thread_window .o_composer_text_field').click();
    assert.strictEqual(document.activeElement,
        $('.o_thread_window .o_composer_text_field')[0],
        "thread window's input should now be focused");

    framework.unblockUI();
    parent.destroy();
});

QUnit.test('emoji popover should open correctly in thread windows', function (assert) {
    assert.expect(1);

    var parent = this.createParent({
        data: this.data,
        services: this.services,
    });

    // get channel instance to link to thread window
    var channel = parent.call('mail_service', 'getChannel', 1);
    channel.detach();

    var $emojiButton = $('.o_composer_button_emoji');
    $emojiButton.trigger('focusin').focus().click();
    var $popover = $('.o_mail_emoji_container');

    var done = assert.async();
    // Async is needed as the popover focusout hiding is deferred
    setTimeout(function () {
        assert.ok($popover.is(':visible'), "emoji popover should have stayed opened");
        parent.destroy();
        done();
    }, 0);
});

QUnit.test('do not increase unread counter when receiving message with myself as author', function (assert) {
    assert.expect(4);

    var parent = this.createParent({
        data: this.data,
        services: this.services,
        session: { partner_id: 3 }
    });

    // get channel instance to link to thread window
    var channel = parent.call('mail_service', 'getChannel', 1);
    channel.detach();

    var threadWindowHeaderText = $('.o_thread_window_header').text().replace(/\s/g, "");

    assert.strictEqual(threadWindowHeaderText, "#general",
        "thread window header text should not have any unread counter initially");
    assert.strictEqual(channel.getUnreadCounter(), 0,
        "thread should have unread counter to 0 initially");

    // simulate receiving message from myself
    var messageData = {
        author_id: [3, "Myself"],
        body: "<p>Test message</p>",
        id: 2,
        model: 'mail.channel',
        res_id: 1,
        channel_ids: [1],
    };
    var notification = [[false, 'mail.channel', 1], messageData];
    parent.call('bus_service', 'trigger', 'notification', [notification]);

    threadWindowHeaderText = $('.o_thread_window_header').text().replace(/\s/g, "");

    assert.strictEqual(threadWindowHeaderText, "#general",
        "thread window header text should not have any unread counter after receiving my message");
    assert.strictEqual(channel.getUnreadCounter(), 0,
        "thread should not have incremented its unread counter after receiving my message");

    parent.destroy();
});

QUnit.test('do not increment unread counter with focus on thread window', function (assert) {
    // 'hard' focus means that the user has clicked on the thread window in
    // order to set the focus on it.
    assert.expect(2);

    var parent = this.createParent({
        data: this.data,
        services: this.services,
        session: { partner_id: 3 }
    });

    // get channel instance to link to thread window
    var channel = parent.call('mail_service', 'getChannel', 1);
    channel.detach();

    assert.strictEqual(channel.getUnreadCounter(), 0,
        "thread should have unread counter to 0 initially");

    // hard focus on thread window composer
    $('.o_composer_text_field').click();

    // simulate receiving message from someone else
    var messageData = {
        author_id: [5, "Someone else"],
        body: "<p>Test message</p>",
        id: 2,
        model: 'mail.channel',
        res_id: 1,
        channel_ids: [1],
    };
    var notification = [[false, 'mail.channel', 1], messageData];
    parent.call('bus_service', 'trigger', 'notification', [notification]);

    assert.strictEqual(channel.getUnreadCounter(), 0,
        "thread should not have incremented its unread counter after receiving the message");

    parent.destroy();
});

QUnit.test('do not mark as read the newly open thread window from received message', function (assert) {
    assert.expect(5);

    this.data['mail.channel'] = {
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
            message_unread_counter: {
                string: "Amount of Unread Messages",
                type: "integer"
            },
        },
        records: [{
            id: 2,
            name: "DM",
            channel_type: "chat",
            message_unread_counter: 0,
        }],
    };

    var parent = this.createParent({
        data: this.data,
        services: this.services,
        session: { partner_id: 3 },
        mockRPC: function (route, args) {
            if (args.method === 'channel_join_and_get_info') {
                this.data['mail.channel'].records[0].state = 'open';
                this.data['mail.channel'].records[0].is_minimized = true;
                return $.when(this.data['mail.channel'].records[0]);
            }
            return this._super.apply(this, arguments);
        },
    });

    assert.strictEqual($('.o_thread_window').length, 0,
        "no thread window should be open initially");

    // simulate receiving message from someone else in DM
    var messageData = {
        author_id: [5, "Someone else"],
        body: "<p>Test message</p>",
        id: 2,
        model: 'mail.channel',
        res_id: 1,
        channel_ids: [2],
    };
    var notification = [[false, 'mail.channel', 1], messageData];
    // Unread counter is obtained from fetched channel data, because this is
    // a new message from a new channel.
    this.data['mail.channel'].records[0].message_unread_counter++;
    parent.call('bus_service', 'trigger', 'notification', [notification]);

    var $threadWindow = $('.o_thread_window');
    assert.strictEqual($threadWindow.length, 1,
        "a thread window should be open after receiving a new message on a new DM chat");
    assert.strictEqual($threadWindow.data('thread-id'), 2,
        "open thread window should be related to DM chat");
    assert.strictEqual($threadWindow.find('.o_thread_window_title').text().replace(/\s/g, ''), '#DM(1)',
        "open DM chat window should have one unread message");

    $threadWindow.find('.o_thread_composer').click();
    assert.strictEqual($threadWindow.find('.o_thread_window_title').text().replace(/\s/g, ''), '#DM',
        "open DM chat window should have message marked as read on composer focus");

    parent.destroy();
});

});
});
});
