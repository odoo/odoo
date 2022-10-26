/** @odoo-module **/

import { afterNextRender, start, startServer } from '@mail/../tests/helpers/test_utils';

import { patchWithCleanup } from '@web/../tests/helpers/utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('notification_list_notification_group_tests.js');

QUnit.test('notification group basic layout', async function (assert) {
    assert.expect(10);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    const mailMessageId1 = pyEnv['mail.message'].create({
        message_type: 'email', // message must be email (goal of the test)
        model: 'mail.channel', // expected value to link message to channel
        res_id: mailChannelId1,
        res_model_name: "Channel", // random res model name, will be asserted in the test
    });
    pyEnv['mail.notification'].create([
        {
            mail_message_id: mailMessageId1,
            notification_status: 'exception',
            notification_type: 'email',
        },
        {
            mail_message_id: mailMessageId1,
            notification_status: 'exception',
            notification_type: 'email',
        },
    ]);
    const { click } = await start();
    await click('.o_MessagingMenu_toggler');
    assert.containsOnce(
        document.body,
        '.o_NotificationGroup',
        "should have 1 notification group"
    );
    assert.containsOnce(
        document.body,
        '.o_NotificationGroup_name',
        "should have 1 group name"
    );
    assert.strictEqual(
        document.querySelector('.o_NotificationGroup_name').textContent,
        "Channel",
        "should have model name as group name"
    );
    assert.containsOnce(
        document.body,
        '.o_NotificationGroup_counter',
        "should have 1 group counter"
    );
    assert.strictEqual(
        document.querySelector('.o_NotificationGroup_counter').textContent.trim(),
        "(2)",
        "should have 2 notifications in the group"
    );
    assert.containsOnce(
        document.body,
        '.o_NotificationGroup_date',
        "should have 1 group date"
    );
    assert.strictEqual(
        document.querySelector('.o_NotificationGroup_date').textContent,
        "a few seconds ago",
        "should have the group date corresponding to now"
    );
    assert.containsOnce(
        document.body,
        '.o_NotificationGroup_inlineText',
        "should have 1 group text"
    );
    assert.strictEqual(
        document.querySelector('.o_NotificationGroup_inlineText').textContent.trim(),
        "An error occurred when sending an email.",
        "should have the group text corresponding to email"
    );
    assert.containsOnce(
        document.body,
        '.o_NotificationGroup_markAsRead',
        "should have 1 mark as read button"
    );
});

QUnit.test('mark as read', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    const mailMessageId1 = pyEnv['mail.message'].create({
        message_type: 'email', // message must be email (goal of the test)
        model: 'mail.channel', // expected value to link message to channel
        res_id: mailChannelId1,
        res_model_name: "Channel", // random res model name, will be asserted in the test
    });
    // failure that is expected to be used in the test
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId1, // id of the related message
        notification_status: 'exception', // necessary value to have a failure
        notification_type: 'email',
    });
    const { click } = await start();
    await click('.o_MessagingMenu_toggler');
    assert.containsOnce(
        document.body,
        '.o_NotificationGroup_markAsRead',
        "should have 1 mark as read button"
    );

    await afterNextRender(() => {
        document.querySelector('.o_NotificationGroup_markAsRead').click();
    });
    assert.containsNone(
        document.body,
        '.o_NotificationGroup',
        "should have no notification group"
    );
});

QUnit.test('grouped notifications by document', async function (assert) {
    // If some failures linked to a document refers to a same document, a single
    // notification should group all those failures.
    assert.expect(5);

    const pyEnv = await startServer();
    const [mailMessageId1, mailMessageId2] = pyEnv['mail.message'].create([
        // first message that is expected to have a failure
        {
            message_type: 'email', // message must be email (goal of the test)
            model: 'res.partner', // same model as second message (and not `mail.channel`)
            res_id: 31, // same res_id as second message
            res_model_name: "Partner", // random related model name
        },
        // second message that is expected to have a failure
        {
            message_type: 'email', // message must be email (goal of the test)
            model: 'res.partner', // same model as first message (and not `mail.channel`)
            res_id: 31, // same res_id as first message
            res_model_name: "Partner", // same related model name for consistency
        },
    ]);
    pyEnv['mail.notification'].create([
        // first failure that is expected to be used in the test
        {
            mail_message_id: mailMessageId1, // id of the related first message
            notification_status: 'exception', // one possible value to have a failure
            notification_type: 'email', // expected failure type for email message
        },
        // second failure that is expected to be used in the test
        {
            mail_message_id: mailMessageId2, // id of the related second message
            notification_status: 'bounce', // other possible value to have a failure
            notification_type: 'email', // expected failure type for email message
        }
    ]);
    const { click } = await start();
    await click('.o_MessagingMenu_toggler');

    assert.containsOnce(
        document.body,
        '.o_NotificationGroup',
        "should have 1 notification group"
    );
    assert.containsOnce(
        document.body,
        '.o_NotificationGroup_counter',
        "should have 1 group counter"
    );
    assert.strictEqual(
        document.querySelector('.o_NotificationGroup_counter').textContent.trim(),
        "(2)",
        "should have 2 notifications in the group"
    );
    assert.containsNone(
        document.body,
        '.o_ChatWindow',
        "should have no chat window initially"
    );

    await click('.o_NotificationGroup');
    assert.containsOnce(
        document.body,
        '.o_ChatWindow',
        "should have opened the thread in a chat window after clicking on it"
    );
});

QUnit.test('grouped notifications by document model', async function (assert) {
    // If all failures linked to a document model refers to different documents,
    // a single notification should group all failures that are linked to this
    // document model.
    assert.expect(12);

    const pyEnv = await startServer();
    const [mailMessageId1, mailMessageId2] = pyEnv['mail.message'].create([
        // first message that is expected to have a failure
        {
            message_type: 'email', // message must be email (goal of the test)
            model: 'res.partner', // same model as second message (and not `mail.channel`)
            res_id: 31, // different res_id from second message
            res_model_name: "Partner", // random related model name
        },
        // second message that is expected to have a failure
        {
            message_type: 'email', // message must be email (goal of the test)
            model: 'res.partner', // same model as first message (and not `mail.channel`)
            res_id: 32, // different res_id from first message
            res_model_name: "Partner", // same related model name for consistency
        },
    ]);
    pyEnv['mail.notification'].create([
        // first failure that is expected to be used in the test
        {
            mail_message_id: mailMessageId1, // id of the related first message
            notification_status: 'exception', // one possible value to have a failure
            notification_type: 'email', // expected failure type for email message
        },
        // second failure that is expected to be used in the test
        {
            mail_message_id: mailMessageId2, // id of the related second message
            notification_status: 'bounce', // other possible value to have a failure
            notification_type: 'email', // expected failure type for email message
        },
    ]);

    const { click, env } = await start();
    patchWithCleanup(env.services.action, {
        doAction(action) {
            assert.step('do_action');
            assert.strictEqual(
                action.name,
                "Mail Failures",
                "action should have 'Mail Failures' as name",
            );
            assert.strictEqual(
                action.type,
                'ir.actions.act_window',
                "action should have the type act_window"
            );
            assert.strictEqual(
                action.view_mode,
                'kanban,list,form',
                "action should have 'kanban,list,form' as view_mode"
            );
            assert.strictEqual(
                JSON.stringify(action.views),
                JSON.stringify([[false, 'kanban'], [false, 'list'], [false, 'form']]),
                "action should have correct views"
            );
            assert.strictEqual(
                action.target,
                'current',
                "action should have 'current' as target"
            );
            assert.strictEqual(
                action.res_model,
                'res.partner',
                "action should have the group model as res_model"
            );
            assert.strictEqual(
                JSON.stringify(action.domain),
                JSON.stringify([['message_has_error', '=', true]]),
                "action should have 'message_has_error' as domain"
            );
        },
    });
    await click('.o_MessagingMenu_toggler');

    assert.containsOnce(
        document.body,
        '.o_NotificationGroup',
        "should have 1 notification group"
    );
    assert.containsOnce(
        document.body,
        '.o_NotificationGroup_counter',
        "should have 1 group counter"
    );
    assert.strictEqual(
        document.querySelector('.o_NotificationGroup_counter').textContent.trim(),
        "(2)",
        "should have 2 notifications in the group"
    );

    document.querySelector('.o_NotificationGroup').click();
    assert.verifySteps(
        ['do_action'],
        "should do an action to display the related records"
    );
});

QUnit.test('different mail.channel are not grouped', async function (assert) {
    // `mail.channel` is a special case where notifications are not grouped when
    // they are linked to different channels, even though the model is the same.
    assert.expect(6);

    const pyEnv = await startServer();
    const [mailChannelId1, mailChannelId2] = pyEnv['mail.channel'].create([{ name: "mailChannel1" }, { name: "mailChannel2" }]);
    const [mailMessageId1, mailMessageId2] = pyEnv['mail.message'].create([
        // first message that is expected to have a failure
        {
            message_type: 'email', // message must be email (goal of the test)
            model: 'mail.channel', // testing a channel is the goal of the test
            res_id: mailChannelId1, // different res_id from second message
            res_model_name: "Channel", // random related model name
        },
        // second message that is expected to have a failure
        {
            message_type: 'email', // message must be email (goal of the test)
            model: 'mail.channel', // testing a channel is the goal of the test
            res_id: mailChannelId2, // different res_id from first message
            res_model_name: "Channel", // same related model name for consistency
        },
    ]);
    pyEnv['mail.notification'].create([
        {
            mail_message_id: mailMessageId1, // id of the related first message
            notification_status: 'exception', // one possible value to have a failure
            notification_type: 'email', // expected failure type for email message
        },
        {
            mail_message_id: mailMessageId1,
            notification_status: 'exception',
            notification_type: 'email',
        },
        {
            mail_message_id: mailMessageId2, // id of the related second message
            notification_status: 'bounce', // other possible value to have a failure
            notification_type: 'email', // expected failure type for email message
        },
        {
            mail_message_id: mailMessageId2,
            notification_status: 'bounce',
            notification_type: 'email',
        },
    ]);
    const { click } = await start();
    await click('.o_MessagingMenu_toggler');
    assert.containsN(
        document.body,
        '.o_NotificationGroup',
        2,
        "should have 2 notifications group"
    );
    const groups = document.querySelectorAll('.o_NotificationGroup');
    assert.containsOnce(
        groups[0],
        '.o_NotificationGroup_counter',
        "should have 1 group counter in first group"
    );
    assert.strictEqual(
        groups[0].querySelector('.o_NotificationGroup_counter').textContent.trim(),
        "(2)",
        "should have 2 notifications in first group"
    );
    assert.containsOnce(
        groups[1],
        '.o_NotificationGroup_counter',
        "should have 1 group counter in second group"
    );
    assert.strictEqual(
        groups[1].querySelector('.o_NotificationGroup_counter').textContent.trim(),
        "(2)",
        "should have 2 notifications in second group"
    );

    await afterNextRender(() => groups[0].click());
    assert.containsOnce(
        document.body,
        '.o_ChatWindow',
        "should have opened the channel related to the first group in a chat window"
    );
});

QUnit.test('multiple grouped notifications by document model, sorted by the most recent message of each group', async function (assert) {
    assert.expect(9);

    const pyEnv = await startServer();
    const [mailMessageId1, mailMessageId2] = pyEnv['mail.message'].create([
        // first message that is expected to have a failure
        {
            message_type: 'email', // message must be email (goal of the test)
            model: 'res.partner', // different model from second message
            res_id: 31,
            res_model_name: "Partner", // random related model name
        },
        // second message that is expected to have a failure
        {
            message_type: 'email', // message must be email (goal of the test)
            model: 'res.company', // different model from first message
            res_id: 32,
            res_model_name: "Company", // random related model name
        },
    ]);
    pyEnv['mail.notification'].create([
        {
            mail_message_id: mailMessageId1, // id of the related first message
            notification_status: 'exception', // one possible value to have a failure
            notification_type: 'email', // expected failure type for email message
        },
        {
            mail_message_id: mailMessageId1,
            notification_status: 'exception',
            notification_type: 'email',
        },
        {
            mail_message_id: mailMessageId2, // id of the related second message
            notification_status: 'bounce', // other possible value to have a failure
            notification_type: 'email', // expected failure type for email message
        },
        {
            mail_message_id: mailMessageId2,
            notification_status: 'bounce',
            notification_type: 'email',
        },
    ]);
    const { click } = await start();
    await click('.o_MessagingMenu_toggler');
    assert.containsN(
        document.body,
        '.o_NotificationGroup',
        2,
        "should have 2 notifications group"
    );
    const groups = document.querySelectorAll('.o_NotificationGroup');
    assert.containsOnce(
        groups[0],
        '.o_NotificationGroup_name',
        "should have 1 group name in first group"
    );
    assert.strictEqual(
        groups[0].querySelector('.o_NotificationGroup_name').textContent,
        "Company",
        "should have first model name as group name"
    );
    assert.containsOnce(
        groups[0],
        '.o_NotificationGroup_counter',
        "should have 1 group counter in first group"
    );
    assert.strictEqual(
        groups[0].querySelector('.o_NotificationGroup_counter').textContent.trim(),
        "(2)",
        "should have 2 notifications in first group"
    );
    assert.containsOnce(
        groups[1],
        '.o_NotificationGroup_name',
        "should have 1 group name in second group"
    );
    assert.strictEqual(
        groups[1].querySelector('.o_NotificationGroup_name').textContent,
        "Partner",
        "should have second model name as group name"
    );
    assert.containsOnce(
        groups[1],
        '.o_NotificationGroup_counter',
        "should have 1 group counter in second group"
    );
    assert.strictEqual(
        groups[1].querySelector('.o_NotificationGroup_counter').textContent.trim(),
        "(2)",
        "should have 2 notifications in second group"
    );
});

QUnit.test('non-failure notifications are ignored', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const mailMessageId1 = pyEnv['mail.message'].create({
            message_type: 'email', // message must be email (goal of the test)
            model: 'res.partner', // random model
            res_id: resPartnerId1,
    });
    pyEnv['mail.notification'].create({
            mail_message_id: mailMessageId1, // id of the related first message
            notification_status: 'ready', // non-failure status
            notification_type: 'email', // expected notification type for email message
    });
    const { click } = await start();
    await click('.o_MessagingMenu_toggler');
    assert.containsNone(
        document.body,
        '.o_NotificationGroup',
        "should have 0 notification group"
    );
});

});
});
