odoo.define('mail.chat_window_test', function (require) {
"use strict";

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
        assert.strictEqual(chatWindow.$input[0], document.activeElement,
            "input should be focused");
        var upKeyEvent = jQuery.Event( "keyup", {which: 27});
        chatWindow.$('.o_composer_input').trigger(upKeyEvent);
        assert.strictEqual(chatWindow.folded, false, "Closed chat Window");
        chatWindow.destroy();
    });

});
});
