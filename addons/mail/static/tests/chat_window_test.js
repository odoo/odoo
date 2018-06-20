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

    QUnit.test('open document viewer and close using ESCAPE key should reset focus to chat window', function (assert) {
        assert.expect(6);

        function createParent(params) {
            var widget = new Widget();

            testUtils.addMockEnvironment(widget, params);
            return widget;
        }
        var messages = [{
            attachment_ids: [{
                filename: 'image1.jpg',
                id:1,
                mimetype: 'image/jpeg',
                name: 'Test Image 1',
                url: '/web/content/1?download=true'
            }],
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
            mockRPC: function (route, args) {
                if(_.str.contains(route, '/mail/attachment/preview/') ||
                    _.str.contains(route, '/web/static/lib/pdfjs/web/viewer.html')){
                    var canvas = document.createElement('canvas');
                    return $.when(canvas.toDataURL());
                }
                return this._super.apply(this, arguments);
            },
            data: {},
        });

        var chatWindow = new ChatWindow(parent, 1, "user", false, messages.length, {});
        chatWindow.appendTo($('#qunit-fixture'));
        chatWindow.render(messages);

        testUtils.intercept(chatWindow, 'get_messages', function(event) {
            event.stopPropagation();
            var requested_msgs = _.filter(messages, function (msg) {
                return _.contains(event.data.options.ids, msg.id);
            });
            event.data.callback($.when(requested_msgs));
        }, true);

        testUtils.intercept(chatWindow, 'get_bus', function(event) {
            event.stopPropagation();
            event.data.callback(new Bus());
        }, true);

        chatWindow.on('document_viewer_closed', null, function () {
            assert.ok(true, "chat window should trigger a close document viewer event");
        });
        assert.strictEqual(chatWindow.$('.o_thread_message .o_attachment').length, 1,
        "there should be three attachment on message");
        // click on first image attachement
        chatWindow.$('.o_thread_message .o_attachment .o_image_box .o_image_overlay').first().click();
        // check focus is on document viewer popup and then press escape to close it
        assert.strictEqual(document.activeElement, $('.o_modal_fullscreen')[0], "Modal popup should have focus");
        assert.strictEqual($('.o_modal_fullscreen img.o_viewer_img[src*="/web/image/1?unique=1"]').length, 1,
            "Modal popup should open with first image src");
        // trigger ESCAPE keyup on document viewer popup
        var upKeyEvent = jQuery.Event("keyup", {which: 27});
        $('.o_modal_fullscreen').trigger(upKeyEvent);
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
