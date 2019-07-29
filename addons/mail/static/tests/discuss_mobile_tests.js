odoo.define('mail.discuss_mobile_tests', function (require) {
"use strict";

var mailTestUtils = require('mail.testUtils');

var testUtils = require('web.test_utils');
var concurrency = require('web.concurrency');
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

QUnit.test('mobile discuss swipe [Mark as Read and Toggle Star]', async function (assert) {
    var done = assert.async();
    assert.expect(8);

    this.data['mail.message'].records = [{
        author_id: ["1", "John Doe 1"],
        body: '<p>Test Message</p>',
        date: "2019-03-20 09:35:40",
        id: 1,
        is_discussion: true,
        is_starred: false,
        res_id: 1,
        needaction: true,
        needaction_partner_ids: [3],
    }];
    var objectDiscuss;
    createDiscuss({
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
                assert.step('toggle_star_status');
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
                objectDiscuss.call('bus_service', 'trigger', 'notification', [notification]);
                return Promise.resolve();
            }
            return this._super.apply(this, arguments);
        },
    }).then(function (discuss) {
        objectDiscuss = discuss;
        var $message = discuss.$('.o_thread_message_mobile.list_swipe_actions').eq(0);
        assert.ok($message.find('.swipe-action.left').length, 'Thread message should have left action for mark as read');
        assert.ok($message.find('.swipe-action.right').length, 'Thread message should have right action for toggle star');

        var topOffset = $message.offset().top - 30;

        new Promise(function (resolve) {
            var rightOffset = $message.width() - 50;
            $message = discuss.$('.o_thread_message_mobile.list_swipe_actions').eq(0);
            // Left side swipe for Toggle Star
            var touchStart = $.Event( "touchstart", {
                changedTouches: [{
                    clientX: rightOffset,
                    clientY: topOffset
                }]
            });
            testUtils.dom.triggerEvents($message, [touchStart, 'click']);

            var touchMove = $.Event( "touchmove", {
                changedTouches: [{
                    clientX: rightOffset - 100,
                    clientY: topOffset
                }]
            });
            testUtils.dom.triggerEvents($message, [touchMove, 'click']);

            var touchEnd = $.Event( "touchend", {
                changedTouches: [{
                    clientX: 400,
                    clientY: topOffset
                }]
            });
            testUtils.dom.triggerEvents($message, [touchEnd, 'click']);
            concurrency.delay(750).then(function () {
                assert.verifySteps(['toggle_star_status'], "thread message should starred");
                assert.ok(discuss.$('.o_thread_message .o_thread_message_star.fa-star').length, "messages should be starred");
                resolve();
            });
        }).then(function () {
            // Right side swipe for mark as read
            $message = discuss.$('.o_thread_message_mobile.list_swipe_actions').eq(0);
            var touchStart = $.Event( "touchstart", {
                changedTouches: [{
                    clientX: 20,
                    clientY: topOffset
                }]
            });
            testUtils.dom.triggerEvents($message, [touchStart, 'click']);

            var touchMove = $.Event( "touchmove", {
                changedTouches: [{
                    clientX: 200,
                    clientY: topOffset
                }]
            });
            testUtils.dom.triggerEvents($message, [touchMove, 'click']);

            var touchEnd = $.Event( "touchend", {
                changedTouches: [{
                    clientX: 400,
                    clientY: topOffset
                }]
            });
            testUtils.dom.triggerEvents($message, [touchEnd, 'click']);
            // jQuery animation delay
            concurrency.delay(650).then(function () {
                assert.ok($('body > .o_mobile_undobar').length, 'showing undo option for marked as read');
                // waiting for undo to go
                return concurrency.delay(3000);
            }).then(function () {
                assert.verifySteps(['mark_as_read'], "thread should marked as read");
                discuss.destroy();
                done();
            });
        });
    });
});
});
});
