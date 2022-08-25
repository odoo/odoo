/** @odoo-module **/

import { start, startServer } from '@mail/../tests/helpers/test_utils';

import { patchWithCleanup } from '@web/../tests/helpers/utils';

QUnit.module('sms', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('notification_list', {}, function () {
QUnit.module('notification_list_notification_group_tests.js');

QUnit.test('mark as read', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    const mailMessageId1 = pyEnv['mail.message'].create(
        // message that is expected to have a failure
        {
            author_id: pyEnv.currentPartnerId,
            message_type: 'sms',
            model: 'mail.channel',
            res_id: mailChannelId1,
        }
    );
    pyEnv['mail.notification'].create(
        // failure that is expected to be used in the test
        {
            mail_message_id: mailMessageId1, // id of the related message
            notification_status: 'exception', // necessary value to have a failure
            notification_type: 'sms',
        }
    );
    const { afterNextRender, click } = await start();
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

QUnit.test('notifications grouped by notification_type', async function (assert) {
    assert.expect(11);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const [mailMessageId1, mailMessageId2] = pyEnv['mail.message'].create([
        {
            message_type: 'sms', // different type from second message
            model: 'res.partner', // same model as second message (and not `mail.channel`)
            res_id: resPartnerId1, // same res_id as second message
            res_model_name: "Partner", // random related model name
        },
        {
            message_type: 'email', // different type from first message
            model: 'res.partner', // same model as first message (and not `mail.channel`)
            res_id: resPartnerId1, // same res_id as first message
            res_model_name: "Partner", // same related model name for consistency
        },
    ]);
    pyEnv['mail.notification'].create([
        {
            mail_message_id: mailMessageId1, // id of the related first message
            notification_status: 'exception', // necessary value to have a failure
            notification_type: 'sms', // different type from second failure
        },
        {
            mail_message_id: mailMessageId1,
            notification_status: 'exception',
            notification_type: 'sms',
        },
        {
            mail_message_id: mailMessageId2, // id of the related second message
            notification_status: 'exception', // necessary value to have a failure
            notification_type: 'email', // different type from first failure
        },
        {
            mail_message_id: mailMessageId2,
            notification_status: 'exception',
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
        "Partner",
        "should have model name as group name"
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
    assert.strictEqual(
        groups[0].querySelector('.o_NotificationGroup_inlineText').textContent.trim(),
        "An error occurred when sending an email.",
        "should have the group text corresponding to email"
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
    assert.strictEqual(
        groups[1].querySelector('.o_NotificationGroup_inlineText').textContent.trim(),
        "An error occurred when sending an SMS.",
        "should have the group text corresponding to sms"
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
            message_type: 'sms', // message must be sms (goal of the test)
            model: 'res.partner', // same model as second message (and not `mail.channel`)
            res_id: 31, // different res_id from second message
            res_model_name: "Partner", // random related model name
        },
        // second message that is expected to have a failure
        {
            message_type: 'sms', // message must be sms (goal of the test)
            model: 'res.partner', // same model as first message (and not `mail.channel`)
            res_id: 32, // different res_id from first message
            res_model_name: "Partner", // same related model name for consistency
        },
    ]);
    pyEnv['mail.notification'].create([
        // first failure that is expected to be used in the test
        {
            mail_message_id: mailMessageId1, // id of the related first message
            notification_status: 'exception', // necessary value to have a failure
            notification_type: 'sms', // expected failure type for sms message
        },
        // second failure that is expected to be used in the test
        {
            mail_message_id: mailMessageId2, // id of the related second message
            notification_status: 'exception', // necessary value to have a failure
            notification_type: 'sms', // expected failure type for sms message
        },
    ]);
    const { click, env } = await start();
    patchWithCleanup(env.services.action, {
        doAction(action) {
            assert.step('do_action');
            assert.strictEqual(
                action.name,
                "SMS Failures",
                "action should have 'SMS Failures' as name",
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
                JSON.stringify([['message_has_sms_error', '=', true]]),
                "action should have 'message_has_sms_error' as domain"
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

});
});
});
