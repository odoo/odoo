/** @odoo-module **/

import { afterNextRender, start, startServer } from '@mail/../tests/helpers/test_utils';

import { patchWithCleanup } from '@web/../tests/helpers/utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_needaction_preview_tests.js');

QUnit.test('mark as read', async function (assert) {
    assert.expect(5);

    const pyEnv = await startServer();
    const resPartnerId1 =  pyEnv['res.partner'].create({});
    const mailMessageId1 = pyEnv['mail.message'].create({
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [pyEnv.currentPartnerId],
        res_id: resPartnerId1,
    });
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId1,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { afterEvent, click, messaging } = await start({
        async mockRPC(route, args) {
            if (route.includes('mark_all_as_read')) {
                assert.step('mark_all_as_read');
                assert.deepEqual(
                    args.kwargs.domain,
                    [
                        ['model', '=', 'res.partner'],
                        ['res_id', '=', resPartnerId1],
                    ],
                    "should mark all as read the correct thread"
                );
            }
        },
    });
    await afterNextRender(() => afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread === messaging.inbox.thread;
        },
    }));
    assert.containsOnce(
        document.body,
        '.o_ThreadNeedactionPreview_markAsRead',
        "should have 1 mark as read button"
    );

    await click('.o_ThreadNeedactionPreview_markAsRead');
    assert.verifySteps(
        ['mark_all_as_read'],
        "should have marked the thread as read"
    );
    assert.containsNone(
        document.body,
        '.o_ChatWindow',
        "should not have opened the thread"
    );
});

QUnit.test('click on preview should mark as read and open the thread', async function (assert) {
    assert.expect(4);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const mailMessageId1 = pyEnv['mail.message'].create({
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [pyEnv.currentPartnerId],
        res_id: resPartnerId1,
    });
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId1,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { afterEvent, click, messaging } = await start();
    await afterNextRender(() => afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread === messaging.inbox.thread;
        },
    }));
    assert.containsOnce(
        document.body,
        '.o_ThreadNeedactionPreview',
        "should have a preview initially"
    );
    assert.containsNone(
        document.body,
        '.o_ChatWindow',
        "should have no chat window initially"
    );

    await click('.o_ThreadNeedactionPreview');
    assert.containsOnce(
        document.body,
        '.o_ChatWindow',
        "should have opened the thread on clicking on the preview"
    );
    await click('.o_MessagingMenu_toggler');
    assert.containsNone(
        document.body,
        '.o_ThreadNeedactionPreview',
        "should have no preview because the message should be marked as read after opening its thread"
    );
});

QUnit.test('click on expand from chat window should close the chat window and open the form view', async function (assert) {
    assert.expect(8);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const mailMessageId1 = pyEnv['mail.message'].create({
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [pyEnv.currentPartnerId],
        res_id: resPartnerId1,
    });
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId1,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { afterEvent, click, env, messaging } = await start();
    patchWithCleanup(env.services.action, {
        doAction(action) {
            assert.step('do_action');
            assert.strictEqual(
                action.res_id,
                resPartnerId1,
                "should redirect to the id of the thread"
            );
            assert.strictEqual(
                action.res_model,
                'res.partner',
                "should redirect to the model of the thread"
            );
        },
    });
    await afterNextRender(() => afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread === messaging.inbox.thread;
        },
    }));
    assert.containsOnce(
        document.body,
        '.o_ThreadNeedactionPreview',
        "should have a preview initially"
    );

    await click('.o_ThreadNeedactionPreview');
    assert.containsOnce(
        document.body,
        '.o_ChatWindow',
        "should have opened the thread on clicking on the preview"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatWindowHeader_commandExpand',
        "should have an expand button"
    );

    await click('.o_ChatWindowHeader_commandExpand');
    assert.containsNone(
        document.body,
        '.o_ChatWindow',
        "should have closed the chat window on clicking expand"
    );
    assert.verifySteps(
        ['do_action'],
        "should have done an action to open the form view"
    );
});

QUnit.test('[technical] opening a non-channel chat window should not call channel_fold', async function (assert) {
    // channel_fold should not be called when opening non-channels in chat
    // window, because there is no server sync of fold state for them.
    assert.expect(3);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const mailMessageId1 = pyEnv['mail.message'].create({
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [pyEnv.currentPartnerId],
        res_id: resPartnerId1,
    });
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId1,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { afterEvent, click, messaging } = await start({
        async mockRPC(route, args) {
            if (route.includes('channel_fold')) {
                const message = "should not call channel_fold when opening a non-channel chat window";
                assert.step(message);
                console.error(message);
                throw Error(message);
            }
        },
    });
    await afterNextRender(() => afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread === messaging.inbox.thread;
        },
    }));
    assert.containsOnce(
        document.body,
        '.o_ThreadNeedactionPreview',
        "should have a preview initially"
    );
    assert.containsNone(
        document.body,
        '.o_ChatWindow',
        "should have no chat window initially"
    );

    await click('.o_ThreadNeedactionPreview');
    assert.containsOnce(
        document.body,
        '.o_ChatWindow',
        "should have opened the chat window on clicking on the preview"
    );
});

QUnit.test('preview should display last needaction message preview even if there is a more recent message that is not needaction in the thread', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({
        name: "Stranger",
    });
    const mailMessageId1 = pyEnv['mail.message'].create({
        author_id: resPartnerId1,
        body: "I am the oldest but needaction",
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [pyEnv.currentPartnerId],
        res_id: resPartnerId1,
    });
    pyEnv['mail.message'].create({
        author_id: pyEnv.currentPartnerId,
        body: "I am more recent",
        model: 'res.partner',
        res_id: resPartnerId1,
    });
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId1,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { afterEvent, messaging } = await start();
    await afterNextRender(() => afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread === messaging.inbox.thread;
        },
    }));
    assert.containsOnce(
        document.body,
        '.o_ThreadNeedactionPreview_inlineText',
        "should have a preview from the last message"
    );
    assert.strictEqual(
        document.querySelector('.o_ThreadNeedactionPreview_inlineText').textContent,
        'Stranger: I am the oldest but needaction',
        "the displayed message should be the one that needs action even if there is a more recent message that is not needaction on the thread"
    );
});

QUnit.test('chat window header should not have unread counter for non-channel thread', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const mailMessageId1 = pyEnv['mail.message'].create({
        author_id: resPartnerId1,
        body: 'not empty',
        model: 'res.partner',
        needaction: true,
        needaction_partner_ids: [pyEnv.currentPartnerId],
        res_id: resPartnerId1,
    });
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId1,
        notification_status: 'sent',
        notification_type: 'inbox',
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { afterEvent, click, messaging } = await start();
    await afterNextRender(() => afterEvent({
        eventName: 'o-thread-cache-loaded-messages',
        func: () => document.querySelector('.o_MessagingMenu_toggler').click(),
        message: "should wait until inbox loaded initial needaction messages",
        predicate: ({ threadCache }) => {
            return threadCache.thread === messaging.inbox.thread;
        },
    }));
    await click('.o_ThreadNeedactionPreview');
    assert.containsOnce(
        document.body,
        '.o_ChatWindow',
        "should have opened the chat window on clicking on the preview"
    );
    assert.containsNone(
        document.body,
        '.o_ChatWindowHeader_counter',
        "chat window header should not have unread counter for non-channel thread"
    );
});

});
});
