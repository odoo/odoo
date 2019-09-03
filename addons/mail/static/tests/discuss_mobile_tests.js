odoo.define('mail.discuss_mobile_tests', function (require) {
"use strict";

var mailTestUtils = require('mail.testUtils');

var testUtils = require('web.test_utils');

var createDiscuss = mailTestUtils.createDiscuss;

QUnit.module('mail', {}, function () {

QUnit.module('Discuss in mobile', {
    beforeEach: function () {
        this.services = mailTestUtils.getMailServices();
        this.data = {
            'mail.channel': {
                fields: {},
            },
            'mail.message': {
                fields: {},
            },
        };
    },
});

QUnit.test('mobile basic rendering', async function (assert) {
    // This is a very basic first test for the client action. However, with
    // the chat_service, it is hard to override RPCs (for instance, the
    // /mail/client_action route is always called when the test suite is
    // launched), and we must wait for this RPC to be done before starting to
    // test the interface. This should be refactored to facilitate the testing.
    assert.expect(16);

    var discuss = await createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
    });
    // test basic rendering in mobile
    assert.containsOnce(discuss, '.o_mail_discuss_content .o_mail_no_content',
        "should display the no content message");
    assert.containsOnce(discuss, '.o_mail_mobile_tabs',
        "should have rendered the tabs");
    assert.hasClass(discuss.$('.o_mail_mobile_tab[data-type=mailbox_inbox]'),'active',
        "should be in inbox tab");
    assert.containsOnce(discuss, '.o_mail_discuss_mobile_mailboxes_buttons:visible',
        "inbox/starred buttons should be visible");
    assert.hasClass(discuss.$('.o_mail_discuss_mobile_mailboxes_buttons .o_mailbox_inbox_item[data-type=mailbox_inbox]'),'btn-primary',
        "should be in inbox");
    assert.hasClass($('.o_mail_discuss_button_dm_chat'),'d-none',
        "should have invisible button 'New Message'");
    assert.hasClass($('.o_mail_discuss_button_multi_user_channel'),'d-none',
        "should have invisible button 'New Channel'");

    // move to 'Chat' tab
    await testUtils.dom.click(discuss.$('.o_mail_mobile_tab[data-type=dm_chat]'));
    assert.hasClass(discuss.$('.o_mail_mobile_tab[data-type=dm_chat]'),'active',
        "should be in 'Chat' tab");
    assert.containsNone(discuss, '.o_mail_discuss_content .o_mail_no_content',
        "should display the no content message");
    assert.strictEqual($('.o_mail_discuss_button_dm_chat').length, 1,
        "should have a button to open DM chat in 'Chat' tab");
    assert.doesNotHaveClass($('.o_mail_discuss_button_dm_chat'), 'd-none',
        "should be visible in 'Chat' tab");
    assert.hasClass($('.o_mail_discuss_button_multi_user_channel'),'d-none',
        "should have invisible button 'New Channel' in 'Chat' tab");
    await testUtils.dom.click($('.o_mail_discuss_button_dm_chat'));
    assert.containsOnce(discuss, '.o_mail_add_thread input:visible',
        "should display the input to add a channel");

    // move to 'Channels' tab
    await testUtils.dom.click(discuss.$('.o_mail_mobile_tab[data-type=multi_user_channel]'));
    assert.hasClass($('.o_mail_discuss_button_dm_chat'),'d-none',
        "should have invisible button 'New Message' in 'Channels' tab");
    assert.doesNotHaveClass($('.o_mail_discuss_button_multi_user_channel'), 'd-none',
        "should have visible button 'New Channel' in 'Channels' tab");
    await testUtils.dom.click($('.o_mail_discuss_button_multi_user_channel')  );
    assert.containsOnce(discuss, '.o_mail_add_thread input:visible',
        "should display the input to add a channel");

    discuss.destroy();
});

QUnit.test('on_{attach/detach}_callback', async function (assert) {
    assert.expect(2);

    var discuss = await createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
    });

    discuss.on_attach_callback();
    assert.ok(true, 'should not crash on attach callback');
    discuss.on_detach_callback();
    assert.ok(true, 'should not crash on detach callback');
    discuss.destroy();
});

QUnit.test('extended composer in mass mailing channel', async function (assert) {
    assert.expect(4);

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [{
                id: 1,
                channel_type: "channel",
                name: "General",
                mass_mailing: true,
            }],
        },
    };

    var discuss = await createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
    });

    await testUtils.dom.click(discuss.$('.o_mail_mobile_tab[data-type="multi_user_channel"]'));
    await testUtils.dom.click(discuss.$('.o_mail_preview[data-preview-id="1"]'));
    assert.containsOnce(
        $,
        '.o_thread_window',
        "should display a chat window");
    assert.strictEqual(
        $('.o_thread_window').data('thread-id'),
        1,
        "chat window should be from channel General");
    assert.containsOnce(
        $('.o_thread_window'),
        '.o_thread_composer',
        "chat window should have a composer");
    assert.ok(
        $('.o_thread_window .o_thread_composer').hasClass('o_thread_composer_extended'),
        "chat window composer should be extended composer");

    discuss.destroy();
});

});
});
