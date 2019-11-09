odoo.define('im_livechat.websiteLivechatWindowTest', function (require) {
"use strict";

const ChatWindow = require('im_livechat.WebsiteLivechatWindow');
const Livechat = require('im_livechat.model.WebsiteLivechat');
const Message = require('im_livechat.model.WebsiteLivechatMessage');

const testUtils = require('web.test_utils');
const Widget = require('web.Widget');

/**
 * Important: the rendering of the website livechat window is not exactly the
 * same as on the website side. This is due to some template extensions from
 * thread windows in the backend. In particular, the 'expand' button should not
 * appear on a website livechat window.
 */
QUnit.module('im_livechat', {}, function () {
QUnit.module('Website Livechat Window', {});

QUnit.test('basic rendering', async function (assert) {
    assert.expect(3);

    var parent = new Widget();
    var livechat = new Livechat({
        parent: parent,
        data: {
            id: 5,
            message_unread_counter: 2,
            name: 'myLivechat',
            operator_pid: [1, "YourOperator"],
        }
    });

    var messages = [];
    for (var i = 0; i < 2; i++) {
        messages.push(new Message(parent, {
            id: i,
            body: "<p>test" + i + "</p>"
        }, {
            default_username: 'defaultUser',
            serverUrl: 'serverUrl',
        }));
    }

    livechat.setMessages(messages);

    var chatWindow = new ChatWindow(parent, livechat);
    testUtils.mock.addMockEnvironment(parent, {});
    await chatWindow.appendTo($('#qunit-fixture'));
    chatWindow.render();

    assert.containsOnce(chatWindow, '.o_thread_window_header',
        "should have a header");
    assert.strictEqual(chatWindow.$('.o_thread_window_header').text().replace(/\s/g, ""),
        "myLivechat(2)",
        "should display the correct livechat name and unread message counter");
    assert.containsN(chatWindow, '.o_thread_message', 2,
        "should display two messages");

    parent.destroy();
});

QUnit.module('LiveChat Tests', {});

QUnit.test('define several livechat colors', async function (assert) {
    assert.expect(2);

    const parent = new Widget();
    const livechat = new Livechat({
        parent,
        data: {
            id: 5,
            message_unread_counter: 2,
            name: "myLivechat",
            operator_pid: [1, "YourOperator"],
        }
    });
    livechat.setMessages([
        new Message(parent, {
            id: 1,
            body: "<p>test1</p>"
        }, {
            default_username: "defaultUser",
            serverUrl: "serverUrl",
        }),
        new Message(parent, {
            id: 2,
            body: "<p>test2</p>"
        }, {
            default_username: "defaultUser",
            serverUrl: "serverUrl",
        }),
    ]);
    const chatWindow = new ChatWindow(parent, livechat, {
        headerBackgroundColor: 'yellow',
        titleColor: 'green',
    });
    testUtils.mock.addMockEnvironment(parent, {});
    await chatWindow.appendTo($('#qunit-fixture'));
    chatWindow.render();
    assert.strictEqual(
        chatWindow.$('.o_thread_window_header').css('background-color'),
        'rgb(255, 255, 0)',
        "header background color should be yellow");
    assert.strictEqual(
        chatWindow.$('.o_thread_window_header').css('color'),
        'rgb(0, 128, 0)',
        "header text color should be green");

    parent.destroy();
});

});
});
