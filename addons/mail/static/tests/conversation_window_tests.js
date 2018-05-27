odoo.define('mail.conversation_window_tests', function (require) {
"use strict";

var ChatService = require('mail.ChatService');
var ConversationWindow = require('mail.widget.ConversationWindow');
var mailTestUtils = require('mail.testUtils');

var framework = require('web.framework');
var testUtils = require('web.test_utils');
var Widget = require('web.Widget');

var createBusService = mailTestUtils.createBusService;

QUnit.module('mail', {
    beforeEach: function () {

        // define channel to link to chat window
        this.data = {
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
        this.services = [ChatService, createBusService()];
    },
}, function () {

    QUnit.module('conversation_window');

    QUnit.test('close conversation window using ESCAPE key', function (assert) {
        assert.expect(4);

        function createParent(params) {
            var widget = new Widget();

            testUtils.addMockEnvironment(widget, params);
            return widget;
        }
        var parent = createParent({
            data: this.data,
            services: this.services,
        });

        // get channel instance to link to conversation window
        var channel = parent.call('chat_service', 'getChannel', 1);
        assert.ok(channel, "there should exist a channel locally with ID 1");

        var conversationWindow = new ConversationWindow(parent, channel);
        conversationWindow.appendTo($('#qunit-fixture'));

        conversationWindow.on('close_chat_session', null, function () {
            assert.ok(true, "conversation window should trigger a close event");
        });
        conversationWindow.threadWidget.$el.trigger("click");
        assert.strictEqual(document.activeElement, conversationWindow.$input[0],
            "input should be focused");
        var upKeyEvent = jQuery.Event( "keyup", { which: 27 });
        conversationWindow.$('.o_composer_input').trigger(upKeyEvent);
        assert.strictEqual(conversationWindow.isFolded(), false, "Closed conversation Window");
        parent.destroy();
    });

    QUnit.test('conversation window\'s input can still be focused when the UI is blocked', function (assert) {
        assert.expect(2);

        function createParent(params) {
            var widget = new Widget();

            testUtils.addMockEnvironment(widget, params);
            return widget;
        }
        var parent = createParent({
            data: this.data,
            services: this.services,
        });

        var $dom = $('#qunit-fixture');

        // get channel instance to link to conversation window
        var channel = parent.call('chat_service', 'getChannel', 1);
        var conversationWindow = new ConversationWindow(parent, channel);
        conversationWindow.appendTo($dom);
        var $input = $('<input/>', {type: 'text'}).appendTo($dom);
        $input.focus().click();
        assert.strictEqual(document.activeElement, $input[0],
            "fake input should be focused");

        framework.blockUI();
        conversationWindow.$input.click(); // cannot force focus here otherwise the test
                                   // makes no sense, this test is just about
                                   // making sure that the code which forces the
                                   // focus on click is not removed
        assert.strictEqual(document.activeElement, conversationWindow.$input[0],
            "conversation window's input should now be focused");

        framework.unblockUI();
        parent.destroy();
    });

    QUnit.test('emoji popover should open correctly in conversation windows', function (assert) {
        assert.expect(1);

        function createParent(params) {
            var widget = new Widget();

            widget.on('get_emojis', widget, function (ev) {
                ev.data.callback([]);
            });

            testUtils.addMockEnvironment(widget, params);
            return widget;
        }
        var parent = createParent({
            data: this.data,
            services: this.services,
        });

        var $dom = $('#qunit-fixture');

        // get channel instance to link to conversation window
        var channel = parent.call('chat_service', 'getChannel', 1);
        var conversationWindow = new ConversationWindow(parent, channel);
        conversationWindow.appendTo($dom);

        var $emojiButton = conversationWindow.$('.o_composer_button_emoji');
        $emojiButton.trigger('focusin').focus().click();
        var $popover = conversationWindow.$('.o_mail_emoji_container');

        var done = assert.async();
        // Async is needed as the popover focusout hiding is deferred
        setTimeout(function () {
            assert.ok($popover.is(':visible'), "emoji popover should have stayed opened");
            parent.destroy();
            done();
        }, 0);
    });
});
});
