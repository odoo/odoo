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

QUnit.test('mobile basic rendering', function (assert) {
    // This is a very basic first test for the client action. However, with
    // the chat_service, it is hard to override RPCs (for instance, the
    // /mail/client_action route is always called when the test suite is
    // launched), and we must wait for this RPC to be done before starting to
    // test the interface. This should be refactored to facilitate the testing.
    assert.expect(19);
    var done = assert.async();

    createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
    }).then(function (discuss) {
        // test basic rendering in mobile
        assert.strictEqual(discuss.$('.o_mail_discuss_content .o_mail_no_content').length, 1,
            "should display the no content message");
        assert.strictEqual(discuss.$('.o_mail_mobile_tabs').length, 1,
            "should have rendered the tabs");
        assert.ok(discuss.$('.o_mail_mobile_tab[data-type=mailbox_inbox]').hasClass('active'),
            "should be in inbox tab");
        assert.strictEqual(discuss.$('.o_mail_discuss_mobile_mailboxes_buttons:visible').length, 1,
            "inbox/starred buttons should be visible");
        assert.ok(discuss.$('.o_mail_discuss_mobile_mailboxes_buttons .o_mailbox_inbox_item[data-type=mailbox_inbox]').hasClass('btn-primary'),
            "should be in inbox");
        assert.ok($('.o_mail_discuss_button_dm_chat').hasClass('d-none'),
            "should have invisible button 'New Message'");
        assert.ok($('.o_mail_discuss_button_public').hasClass('d-none'),
            "should have invisible button 'New Channel'");

        // move to 'Chat' tab
        discuss.$('.o_mail_mobile_tab[data-type=dm_chat]').click();
        assert.ok(discuss.$('.o_mail_mobile_tab[data-type=dm_chat]').hasClass('active'),
            "should be in 'Chat' tab");
        assert.strictEqual(discuss.$('.o_mail_discuss_content .o_mail_no_content').length, 0,
            "should display the no content message");
        assert.strictEqual($('.o_mail_discuss_button_dm_chat').length, 1,
            "should have a button to open DM chat in 'Chat' tab");
        assert.notOk($('.o_mail_discuss_button_dm_chat').hasClass('d-none'),
            "should be visible in 'Chat' tab");
        assert.ok($('.o_mail_discuss_button_public').hasClass('d-none'),
            "should have invisible button 'New Channel' in 'Chat' tab");
        $('.o_mail_discuss_button_dm_chat').click(); // click to open a chat
        assert.strictEqual(discuss.$('.o_mail_add_thread input:visible').length, 1,
            "should display the input to add a channel");

        // move to 'Channels' tab
        discuss.$('.o_mail_mobile_tab[data-type=public]').click();
        assert.ok($('.o_mail_discuss_button_dm_chat').hasClass('d-none'),
            "should have invisible button 'New Message' in 'Channels' tab");
        assert.notOk($('.o_mail_discuss_button_public').hasClass('d-none'),
            "should have visible button 'New Channel' in 'Channels' tab");
        $('.o_mail_discuss_button_public').click(); // click to open a chat
        assert.strictEqual(discuss.$('.o_mail_add_thread input:visible').length, 1,
            "should display the input to add a channel");

        // move to Private Channels tab
        discuss.$('.o_mail_mobile_tab[data-type=private]').click();
        assert.ok($('.o_mail_discuss_button_dm_chat').hasClass('d-none'),
            "should have invisible button 'New Message' in 'Private Channels' tab");
        assert.notOk($('.o_mail_discuss_button_private').hasClass('d-none'),
            "should have invisible button 'New Channel' in 'Private Channels' tab");
        $('.o_mail_discuss_button_private').click(); // click to open a chat
        assert.strictEqual(discuss.$('.o_mail_add_thread input:visible').length, 1,
            "should display the input to add a channel");

        discuss.destroy();
        done();
    });
});

QUnit.test('on_{attach/detach}_callback', function (assert) {
    assert.expect(2);
    var done = assert.async();

    createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
    }).then(function (discuss) {
        try {
            discuss.on_attach_callback();
            assert.ok(true, 'should not crash on attach callback');
            discuss.on_detach_callback();
            assert.ok(true, 'should not crash on detach callback');
        } finally {
            discuss.destroy();
            done();
        }
    });
});

QUnit.test('extended composer in mass mailing channel', function (assert) {
    assert.expect(4);
    var done = assert.async();

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

    createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
    }).then(function (discuss) {
        testUtils.dom.click(discuss.$('.o_mail_mobile_tab[data-type="public"]'));
        testUtils.dom.click(discuss.$('.o_mail_preview[data-preview-id="1"]'));
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
        done();
    });
});

});
});
