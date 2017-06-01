odoo.define('mail.client_action_test', function (require) {
"use strict";

var ActionManager = require('web.ActionManager');
var core = require('web.core');
var config = require('web.config');
var testUtils = require('web.test_utils');
var Widget = require('web.Widget');

var ChatAction = core.action_registry.get('mail.chat.instant_messaging');

QUnit.module('mail', {}, function () {

QUnit.module('ChatAction', {
    beforeEach: function () {
        this.data = {
            "mail.message": {
                fields: {
                    id: {type: 'integer', string: 'ID'}
                }
            }
        };
    }
});

//--------------------------------------------------------------------------
// Mobile Test case
//--------------------------------------------------------------------------

QUnit.test('mobile basic rendering', function (assert) {
    assert.expect(11);

    // Chaning mobile state
    config.isMobile = true;

    function createParent (params) {
        var actionManager = new ActionManager();
        testUtils.addMockEnvironment(actionManager, params);
        return actionManager;
    }

    var action = {
        id: 1,
        context: {'active_channel_id': 'channel_inbox', 'active_ids': ['channel_inbox']},
        params: {'default_active_id': 'channel_inbox'}
    };

    var parent = createParent({
        data: {},
    });

    var chatAction = new ChatAction(parent, action, {});
    chatAction.set_cp_bus(new Widget());

    testUtils.addMockEnvironment(chatAction, {
        data: this.data,
        archs: {
            'mail.message,false,search': '<search/>',
        }
    });
    chatAction.appendTo($('#qunit-fixture'));

    // test for basic view rendering for mobile
    assert.equal(chatAction.$(".o_mail_chat_mobile_control_panel").length, 1, "Mobile control panel created");
    assert.equal(chatAction.$(".o_mail_chat_mobile_tab").length, 4, "Four mobile tabs created");
    assert.equal(chatAction.$('.o_mail_chat_content').length, 1, "One default chat content pane created");
    assert.equal(chatAction.$(".o_mail_chat_tab_pane").length, 3, "Three mobile tab panes created");

    // Inbox
    assert.equal(chatAction.activeMobileTab, "channel_inbox", "'channel_inbox' is default active tab");
    assert.ok(chatAction.$(".o_channel_inbox_item:nth(0)").hasClass("btn-primary"), "Showing 'Inbox'");

    // Starred
    chatAction.mailMobileInboxButtons.find(".o_channel_inbox_item[data-type='channel_starred']").click();
    assert.ok(chatAction.$(".o_channel_inbox_item:nth(1)").hasClass("btn-primary"), "Clicked on 'Starred'");

    assert.ok(chatAction.$(".o_mail_chat_content").is(":visible"), "Default main content pane visible");

    chatAction.$(".o_mail_chat_mobile_tab[data-type='dm']").click();
    assert.equal(chatAction.activeMobileTab, "dm", "After click on 'Conversation', is now active tab");

    assert.ok(!chatAction.$(".o_mail_chat_content").is(":visible"), "none", "'Main' content pane is invisible");
    assert.ok(chatAction.$(".o_mail_chat_tab_pane:nth(0)").is(":visible"), "'Conversation' pane is visible");

    // Restoring mobile state
    config.isMobile = false;

    chatAction.destroy();
});

});
});