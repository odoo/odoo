odoo.define('mail.client_action_mobile_tests', function (require) {
"use strict";

var session = require('web.session');
var testUtils = require('web.test_utils');
var Widget = require('web.Widget');

var ChatAction = require('mail.chat_client_action');
var chat_manager = require('mail.chat_manager');

QUnit.module('mail', {}, function () {

QUnit.module('Discuss client action in mobile', {
    beforeEach: function () {
        this.data = {
            'mail.message': {
                fields: {},
            },
        };
        this.createChatAction = function (params) {
            var Parent = Widget.extend({
                do_push_state: function () {},
            });
            var parent = new Parent();
            testUtils.addMockEnvironment(parent, {
                data: this.data,
                archs: {
                    'mail.message,false,search': '<search/>',
                },
                session: params.session || {},
                intercepts: params.intercepts || {},
            });
            var chatAction = new ChatAction(parent, params);
            chatAction.set_cp_bus(new Widget());
            chatAction.appendTo($('#qunit-fixture'));

            return chatAction;
        };

    },
});

QUnit.test('mobile basic rendering', function (assert) {
    // This is a very basic first test for the client action. However, with
    // the chat_manager, it is hard to override RPCs (for instance, the
    // /mail/client_action route is always called when the test suite is
    // launched), and we must wait for this RPC to be done before starting to
    // test the interface. This should be refactored to facilitate the testing.
    assert.expect(9);
    var done = assert.async();

    var rpc = session.rpc;

    var chatAction = this.createChatAction({
        id: 1,
        context: {},
        params: {},
        intercepts: {
            get_session: function (ev) {
                ev.data.callback({});
            },
        },
        session: {
            rpc: function (route, args) {
                if (args.method === 'message_fetch') {
                    return $.when([]);
                }
                return rpc.apply(this, arguments);
            },
        },
    });

    chat_manager.is_ready.then(function () {
        // test basic rendering in mobile
        assert.strictEqual(chatAction.$('.o_mail_chat_mobile_control_panel').length, 1,
            "should have rendered a control panel");
        assert.strictEqual(chatAction.$('.o_mail_chat_content .o_mail_no_content').length, 1,
            "should display the no content message");
        assert.strictEqual(chatAction.$('.o_mail_mobile_tabs').length, 1,
            "should have rendered the tabs");
        assert.ok(chatAction.$('.o_mail_mobile_tab[data-type=channel_inbox]').hasClass('active'),
            "should be in inbox tab");
        assert.strictEqual(chatAction.$('.o_mail_chat_mobile_inbox_buttons:visible').length, 1,
            "inbox/starred buttons should be visible");
        assert.ok(chatAction.$('.o_mail_chat_mobile_inbox_buttons .o_channel_inbox_item[data-type=channel_inbox]').hasClass('btn-primary'),
            "should be in inbox");

        // move to DMs tab
        chatAction.$('.o_mail_mobile_tab[data-type=dm]').click();
        assert.ok(chatAction.$('.o_mail_mobile_tab[data-type=dm]').hasClass('active'),
            "should be in DMs tab");
        assert.strictEqual(chatAction.$('.o_mail_chat_content .o_mail_no_content').length, 0,
            "should display the no content message");
        chatAction.$('.o_mail_chat_button_dm').click(); // click to add a channel
        assert.strictEqual(chatAction.$('.o_mail_add_channel input:visible').length, 1,
            "should display the input to add a channel");

        chatAction.destroy();
        done();
    });
});

});

});
