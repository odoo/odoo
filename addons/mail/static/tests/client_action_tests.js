odoo.define('mail.client_action_test', function (require) {
"use strict";

var testUtils = require('web.test_utils');
var Widget = require('web.Widget');

var ChatAction = require("mail.chat_client_action");

QUnit.module('mail', {}, function () {

QUnit.module('Discuss client action', {
    beforeEach: function () {
        this.data = {
            'mail.message': {
                fields: {},
            },
        };
        this.createChatAction = function (params) {
            var parent = new Widget();
            testUtils.addMockEnvironment(parent, {
                data: this.data,
                archs: {
                    'mail.message,false,search': '<search/>',
                },
                config: {
                    isMobile: true
                },
            });
            var chatAction = new ChatAction(parent, params);
            chatAction.set_cp_bus(new Widget());
            chatAction.appendTo($('#qunit-fixture'));

            return chatAction;
        };

    },
});

QUnit.skip('mobile basic rendering', function (assert) {
    // Unfortunately, this test is skipped for now because there is no way to
    // execute the whole test suite in mobile (it only works test by test), so
    // as the client action include for mobile is rejected when we are not in
    // mobile, it isn't possible to test it
    // Moreover, RPCs done by the chat_manager (e.g. message_fetch) should be
    // properly mocked.
    assert.expect(11);

    var parent = new Widget();
    testUtils.addMockEnvironment(parent, {
        data: this.data,
        archs: {
            'mail.message,false,search': '<search/>',
        },
        config: {
            isMobile: true,
        },
    });

    var params = {
        id: 1,
        context: {},
        params: {},
    };
    var chatAction = this.createChatAction(params);

    // test basic rendering in mobile
    assert.equal(chatAction.$(".o_mail_chat_mobile_control_panel").length, 1, "Mobile control panel created");
    assert.equal(chatAction.$(".o_mail_mobile_tab").length, 4, "Four mobile tabs created");
    assert.equal(chatAction.$('.o_mail_chat_content').length, 1, "One default chat content pane created");
    assert.equal(chatAction.$(".o_mail_chat_tab_pane").length, 3, "Three mobile tab panes created");

    // Inbox
    assert.equal(chatAction.activeMobileTab, "channel_inbox", "'channel_inbox' is default active tab");
    assert.ok(chatAction.$(".o_channel_inbox_item:nth(0)").hasClass("btn-primary"), "Showing 'Inbox'");

    // Starred
    chatAction.$(".o_channel_inbox_item[data-type='channel_starred']").click();
    assert.ok(chatAction.$(".o_channel_inbox_item:nth(1)").hasClass("btn-primary"), "Clicked on 'Starred'");

    assert.ok(chatAction.$(".o_mail_chat_content").is(":visible"), "Default main content pane visible");

    chatAction.$(".o_mail_mobile_tab[data-type='dm']").click();
    assert.equal(chatAction.activeMobileTab, "dm", "After click on 'Conversation', is now active tab");

    assert.ok(!chatAction.$(".o_mail_chat_content").is(":visible"), "none", "'Main' content pane is invisible");
    assert.ok(chatAction.$(".o_mail_chat_tab_pane:nth(0)").is(":visible"), "'Conversation' pane is visible");

    chatAction.destroy();
});

});
});
