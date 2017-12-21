odoo.define('mail.discuss_mobile_tests', function (require) {
"use strict";

var ChatManager = require('mail.ChatManager');
var mailTestUtils = require('mail.testUtils');

var createBusService = mailTestUtils.createBusService;
var createDiscuss = mailTestUtils.createDiscuss;

QUnit.module('mail', {}, function () {

QUnit.module('Discuss client action in mobile', {
    beforeEach: function () {
        this.BusService = createBusService();
        this.data = {
            'mail.message': {
                fields: {},
            },
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

    var discuss = createDiscuss({
        id: 1,
        context: {},
        params: {},
        mockRPC: function (route, args) {
            if (args.method === 'message_fetch') {
                return $.when([]);
            }
            return this._super.apply(this, arguments);
        },
        services: [ChatManager, this.BusService],
    });

    var chatReady = discuss.call('chat_manager', 'isReady');
    chatReady.then(function () {
        // test basic rendering in mobile
        assert.strictEqual(discuss.$('.o_mail_chat_mobile_control_panel').length, 1,
            "should have rendered a control panel");
        assert.strictEqual(discuss.$('.o_mail_chat_content .o_mail_no_content').length, 1,
            "should display the no content message");
        assert.strictEqual(discuss.$('.o_mail_mobile_tabs').length, 1,
            "should have rendered the tabs");
        assert.ok(discuss.$('.o_mail_mobile_tab[data-type=channel_inbox]').hasClass('active'),
            "should be in inbox tab");
        assert.strictEqual(discuss.$('.o_mail_chat_mobile_inbox_buttons:visible').length, 1,
            "inbox/starred buttons should be visible");
        assert.ok(discuss.$('.o_mail_chat_mobile_inbox_buttons .o_channel_inbox_item[data-type=channel_inbox]').hasClass('btn-primary'),
            "should be in inbox");

        // move to DMs tab
        discuss.$('.o_mail_mobile_tab[data-type=dm]').click();
        assert.ok(discuss.$('.o_mail_mobile_tab[data-type=dm]').hasClass('active'),
            "should be in DMs tab");
        assert.strictEqual(discuss.$('.o_mail_chat_content .o_mail_no_content').length, 0,
            "should display the no content message");
        discuss.$('.o_mail_chat_button_dm').click(); // click to add a channel
        assert.strictEqual(discuss.$('.o_mail_add_channel input:visible').length, 1,
            "should display the input to add a channel");

        discuss.destroy();
        done();
    });
});

});

});
