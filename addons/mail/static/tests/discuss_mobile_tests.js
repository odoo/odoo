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

QUnit.test('mobile discuss swip', async function (assert) {
    assert.expect(5);

    this.data['mail.message'].records = [{
        author_id: ["1", "John Doe 1"],
        body: '<p>test 1</p>',
        date: "2019-03-20 09:35:40",
        id: 1,
        is_discussion: true,
        is_starred: false,
        res_id: 1,
        needaction: true,
        needaction_partner_ids: [3],
    }];

    var swipeStatus;

    // mimic touchSwipe library's swipe method
    $.fn.swipe = function (params) {
        swipeStatus = params.swipeStatus;
    };

    var discuss = await createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        session: { partner_id: 3 },
        mockRPC: function (route, args) {
            if (args.method === 'set_message_done') {
                assert.step('mark_as_read');
            }
            if (args.method === 'toggle_message_starred') {
                var messageData = _.findWhere(
                    this.data['mail.message'].records,
                    { id: args.args[0][0] }
                );
                messageData.is_starred = !messageData.is_starred;
                var data = {
                    info: false,
                    message_ids: [messageData.id],
                    starred: messageData.is_starred,
                    type: 'toggle_star',
                };
                var notification = [[false, 'res.partner'], data];
                discuss.call('bus_service', 'trigger', 'notification', [notification]);
                return Promise.resolve();
            }
            return this._super.apply(this, arguments);
        },
    })

    var $message = discuss.$('.o_thread_message').eq(0);
    // Left side swip
    await testUtils.dom.triggerEvents($message, ['touchstart', 'click']);
    await testUtils.dom.triggerEvents($message, ['touchmove', 'click']);
    assert.ok(discuss.$('.o_thread_message .o_thread_message_star.fa-star-o').length, "messages should be not starred");
    swipeStatus(this,'','left', 200);
    await testUtils.dom.triggerEvents($message, ['touchend', 'click']);
    assert.ok(discuss.$('.o_thread_message .o_thread_message_star.fa-star').length, "messages should be starred");

    // Right side swip
    var $message = discuss.$('.o_thread_message').eq(0);
    await testUtils.dom.triggerEvents($message, ['touchstart', 'click']);
    await testUtils.dom.triggerEvents($message, ['touchmove', 'click']);
    assert.ok(discuss.$('.o_thread_message').length, "messages should be unread");
    swipeStatus(this,'','right', 200);
    assert.verifySteps(['mark_as_read'], "should mail as read");
    await testUtils.dom.triggerEvents($message, ['touchend', 'click']);
    discuss.destroy();
});
});
});
