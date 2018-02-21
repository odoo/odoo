odoo.define('mail.chat_window_test', function (require) {
"use strict";

var framework = require('web.framework');
var testUtils = require('web.test_utils');
var Widget = require('web.Widget');
var ChatWindow = require('mail.ExtendedChatWindow');

QUnit.module('mail', {}, function () {

    QUnit.module('chat_window');

    QUnit.test('close chat window using ESCAPE key', function (assert) {
        assert.expect(3);

        function createParent(params) {
            var widget = new Widget();

            testUtils.addMockEnvironment(widget, params);
            return widget;
        }
        var messages = [{
            attachment_ids: [],
            author_id: ["1", "John Doe"],
            body: "A message",
            date: moment("2016-12-20 09:35:40"),
            displayed_author: "John Doe",
            id: 1,
            is_note: false,
            is_starred: false,
            model: 'partner',
            res_id: 2
        }];
        var parent = createParent({
            data: {},
        });

        var chatWindow = new ChatWindow(parent, 1, "user", false, messages, {});
        chatWindow.appendTo($('#qunit-fixture'));

        chatWindow.on('close_chat_session', null, function () {
            assert.ok(true, "chat window should trigger a close event");
        });
        chatWindow.thread.$el.trigger("click");
        assert.strictEqual(document.activeElement, chatWindow.$input[0],
            "input should be focused");
        var upKeyEvent = jQuery.Event( "keyup", {which: 27});
        chatWindow.$('.o_composer_input').trigger(upKeyEvent);
        assert.strictEqual(chatWindow.folded, false, "Closed chat Window");
        parent.destroy();
    });

    QUnit.test('chat window\'s input can still be focused when the UI is blocked', function (assert) {
        assert.expect(2);

        function createParent(params) {
            var widget = new Widget();

            testUtils.addMockEnvironment(widget, params);
            return widget;
        }
        var parent = createParent({
            data: {},
        });

        var $dom = $('#qunit-fixture');

        var chatWindow = new ChatWindow(parent, 1, "user", false, [], {});
        chatWindow.appendTo($dom);
        var $input = $('<input/>', {type: 'text'}).appendTo($dom);
        $input.focus().click();
        assert.strictEqual(document.activeElement, $input[0],
            "fake input should be focused");

        framework.blockUI();
        chatWindow.$input.click(); // cannot force focus here otherwise the test
                                   // makes no sense, this test is just about
                                   // making sure that the code which forces the
                                   // focus on click is not removed
        assert.strictEqual(document.activeElement, chatWindow.$input[0],
            "chat window's input should now be focused");

        framework.unblockUI();
        parent.destroy();
    });

    QUnit.test('emoji popover should open correctly in chat windows', function (assert) {
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
            data: {},
        });

        var $dom = $('#qunit-fixture');

        var chatWindow = new ChatWindow(parent, 1, "user", false, [], {});
        chatWindow.appendTo($dom);

        var $emojiButton = chatWindow.$('.o_composer_button_emoji');
        $emojiButton.trigger('focusin').focus().click();
        var $popover = chatWindow.$('.o_mail_emoji_container');

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
