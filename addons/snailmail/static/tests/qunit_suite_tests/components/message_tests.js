/** @odoo-module **/

import {
    afterNextRender,
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

import { patchWithCleanup } from '@web/../tests/helpers/utils';

QUnit.module('snailmail', {}, function () {
QUnit.module('components', {}, async function() {
QUnit.module('message_tests.js');

QUnit.test('Sent', async function (assert) {
    assert.expect(8);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({
        name: "Someone",
        partner_share: true,
    });
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: 'not empty',
        message_type: 'snailmail',
        model: 'res.partner',
        res_id: resPartnerId1,
    });
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId1,
        notification_status: 'sent',
        notification_type: 'snail',
        res_partner_id: resPartnerId1,
    });
    const { openFormView } = await start();
    await openFormView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });

    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a message component"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIconClickable',
        "should display the notification icon container"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIcon',
        "should display the notification icon"
    );
    assert.hasClass(
        document.querySelector('.o_Message_notificationIcon'),
        'fa-paper-plane',
        "icon should represent snailmail"
    );

    await afterNextRender(() => {
        document.querySelector('.o_Message_notificationIconClickable').click();
    });
    assert.containsOnce(
        document.body,
        '.o_SnailmailNotificationPopoverContentView',
        "notification popover should be open"
    );
    assert.containsOnce(
        document.body,
        '.o_SnailmailNotificationPopoverContentView_icon',
        "popover should have one icon"
    );
    assert.hasClass(
        document.querySelector('.o_SnailmailNotificationPopoverContentView_icon'),
        'fa-check',
        "popover should have the sent icon"
    );
    assert.strictEqual(
        document.querySelector('.o_SnailmailNotificationPopoverContentView').textContent.trim(),
        "Sent",
        "popover should have the sent text"
    );
});

QUnit.test('Canceled', async function (assert) {
    assert.expect(8);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({
        name: "Someone",
        partner_share: true,
    });
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: 'not empty',
        message_type: 'snailmail',
        model: 'res.partner',
        res_id: resPartnerId1,
    });
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId1,
        notification_status: 'canceled',
        notification_type: 'snail',
        res_partner_id: resPartnerId1,
    });
    const { openFormView } = await start();
    await openFormView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });

    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a message component"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIconClickable',
        "should display the notification icon container"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIcon',
        "should display the notification icon"
    );
    assert.hasClass(
        document.querySelector('.o_Message_notificationIcon'),
        'fa-paper-plane',
        "icon should represent snailmail"
    );

    await afterNextRender(() => {
        document.querySelector('.o_Message_notificationIconClickable').click();
    });
    assert.containsOnce(
        document.body,
        '.o_SnailmailNotificationPopoverContentView',
        "notification popover should be open"
    );
    assert.containsOnce(
        document.body,
        '.o_SnailmailNotificationPopoverContentView_icon',
        "popover should have one icon"
    );
    assert.hasClass(
        document.querySelector('.o_SnailmailNotificationPopoverContentView_icon'),
        'fa-trash-o',
        "popover should have the canceled icon"
    );
    assert.strictEqual(
        document.querySelector('.o_SnailmailNotificationPopoverContentView').textContent.trim(),
        "Canceled",
        "popover should have the canceled text"
    );
});

QUnit.test('Pending', async function (assert) {
    assert.expect(8);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({
        name: "Someone",
        partner_share: true,
    });
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: 'not empty',
        message_type: 'snailmail',
        model: 'res.partner',
        res_id: resPartnerId1,
    });
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId1,
        notification_status: 'ready',
        notification_type: 'snail',
        res_partner_id: resPartnerId1,
    });
    const { openFormView } = await start();
    await openFormView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });

    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a message component"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIconClickable',
        "should display the notification icon container"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIcon',
        "should display the notification icon"
    );
    assert.hasClass(
        document.querySelector('.o_Message_notificationIcon'),
        'fa-paper-plane',
        "icon should represent snailmail"
    );

    await afterNextRender(() => {
        document.querySelector('.o_Message_notificationIconClickable').click();
    });
    assert.containsOnce(
        document.body,
        '.o_SnailmailNotificationPopoverContentView',
        "notification popover should be open"
    );
    assert.containsOnce(
        document.body,
        '.o_SnailmailNotificationPopoverContentView_icon',
        "popover should have one icon"
    );
    assert.hasClass(
        document.querySelector('.o_SnailmailNotificationPopoverContentView_icon'),
        'fa-clock-o',
        "popover should have the pending icon"
    );
    assert.strictEqual(
        document.querySelector('.o_SnailmailNotificationPopoverContentView').textContent.trim(),
        "Awaiting Dispatch",
        "popover should have the pending text"
    );
});

QUnit.test('No Price Available', async function (assert) {
    assert.expect(10);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({
        name: "Someone",
        partner_share: true,
    });
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: 'not empty',
        message_type: 'snailmail',
        model: 'res.partner',
        res_id: resPartnerId1,
    });
    pyEnv['mail.notification'].create({
        failure_type: 'sn_price',
        mail_message_id: mailMessageId1,
        notification_status: 'exception',
        notification_type: 'snail',
        res_partner_id: resPartnerId1,
    });
    const { openFormView } = await start({
        async mockRPC(route, args) {
            if (args.method === 'cancel_letter' && args.model === 'mail.message' && args.args[0][0] === mailMessageId1) {
                assert.step(args.method);
            }
        },
    });
    await openFormView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a message component"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIconClickable',
        "should display the notification icon container"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIcon',
        "should display the notification icon"
    );
    assert.hasClass(
        document.querySelector('.o_Message_notificationIcon'),
        'fa-paper-plane',
        "icon should represent snailmail"
    );

    await afterNextRender(() => {
        document.querySelector('.o_Message_notificationIconClickable').click();
    });
    assert.containsOnce(
        document.body,
        '.o_SnailmailError',
        "error dialog should be open"
    );
    assert.containsOnce(
        document.body,
        '.o_SnailmailError_contentPrice',
        "error dialog should have the 'no price' content"
    );
    assert.containsOnce(
        document.body,
        '.o_SnailmailError_cancelLetterButton',
        "dialog should have a 'Cancel letter' button"
    );

    await afterNextRender(() => {
        document.querySelector('.o_SnailmailError_cancelLetterButton').click();
    });
    assert.containsNone(
        document.body,
        '.o_SnailmailError',
        "dialog should be closed after click on 'Cancel letter'"
    );
    assert.verifySteps(
        ['cancel_letter'],
        "should have made a RPC call to 'cancel_letter'"
    );
});

QUnit.test('Credit Error', async function (assert) {
    assert.expect(11);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({
        name: "Someone",
        partner_share: true,
    });
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: 'not empty',
        message_type: 'snailmail',
        model: 'res.partner',
        res_id: resPartnerId1,
    });
    pyEnv['mail.notification'].create({
        failure_type: 'sn_credit',
        mail_message_id: mailMessageId1,
        notification_status: 'exception',
        notification_type: 'snail',
        res_partner_id: resPartnerId1,
    });
    const { openFormView } = await start({
        async mockRPC(route, args) {
            if (args.method === 'send_letter' && args.model === 'mail.message' && args.args[0][0] === mailMessageId1) {
                assert.step(args.method);
            }
        },
    });
    await openFormView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });

    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a message component"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIconClickable',
        "should display the notification icon container"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIcon',
        "should display the notification icon"
    );
    assert.hasClass(
        document.querySelector('.o_Message_notificationIcon'),
        'fa-paper-plane',
        "icon should represent snailmail"
    );

    await afterNextRender(() => {
        document.querySelector('.o_Message_notificationIconClickable').click();
    });
    assert.containsOnce(
        document.body,
        '.o_SnailmailError',
        "error dialog should be open"
    );
    assert.containsOnce(
        document.body,
        '.o_SnailmailError_contentCredit',
        "error dialog should have the 'credit' content"
    );
    assert.containsOnce(
        document.body,
        '.o_SnailmailError_resendLetterButton',
        "dialog should have a 'Re-send letter' button"
    );
    assert.containsOnce(
        document.body,
        '.o_SnailmailError_cancelLetterButton',
        "dialog should have a 'Cancel letter' button"
    );

    await afterNextRender(() => {
        document.querySelector('.o_SnailmailError_resendLetterButton').click();
    });
    assert.containsNone(
        document.body,
        '.o_SnailmailError',
        "dialog should be closed after click on 'Re-send letter'"
    );
    assert.verifySteps(
        ['send_letter'],
        "should have made a RPC call to 'send_letter'"
    );
});

QUnit.test('Trial Error', async function (assert) {
    assert.expect(11);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({
        name: "Someone",
        partner_share: true,
    });
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: 'not empty',
        message_type: 'snailmail',
        model: 'res.partner',
        res_id: resPartnerId1,
    });
    pyEnv['mail.notification'].create({
        failure_type: 'sn_trial',
        mail_message_id: mailMessageId1,
        notification_status: 'exception',
        notification_type: 'snail',
        res_partner_id: resPartnerId1,
    });
    const { openFormView } = await start({
        async mockRPC(route, args) {
            if (args.method === 'send_letter' && args.model === 'mail.message' && args.args[0][0] === mailMessageId1) {
                assert.step(args.method);
            }
        },
    });
    await openFormView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });

    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a message component"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIconClickable',
        "should display the notification icon container"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIcon',
        "should display the notification icon"
    );
    assert.hasClass(
        document.querySelector('.o_Message_notificationIcon'),
        'fa-paper-plane',
        "icon should represent snailmail"
    );

    await afterNextRender(() => {
        document.querySelector('.o_Message_notificationIconClickable').click();
    });
    assert.containsOnce(
        document.body,
        '.o_SnailmailError',
        "error dialog should be open"
    );
    assert.containsOnce(
        document.body,
        '.o_SnailmailError_contentTrial',
        "error dialog should have the 'trial' content"
    );
    assert.containsOnce(
        document.body,
        '.o_SnailmailError_resendLetterButton',
        "dialog should have a 'Re-send letter' button"
    );
    assert.containsOnce(
        document.body,
        '.o_SnailmailError_cancelLetterButton',
        "dialog should have a 'Cancel letter' button"
    );

    await afterNextRender(() => {
        document.querySelector('.o_SnailmailError_resendLetterButton').click();
    });
    assert.containsNone(
        document.body,
        '.o_SnailmailError',
        "dialog should be closed after click on 'Re-send letter'"
    );
    assert.verifySteps(
        ['send_letter'],
        "should have made a RPC call to 'send_letter'"
    );
});

QUnit.test('Format Error', async function (assert) {
    assert.expect(8);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({
        name: "Someone",
        partner_share: true,
    });
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: 'not empty',
        message_type: 'snailmail',
        model: 'res.partner',
        res_id: resPartnerId1,
    });
    pyEnv['mail.notification'].create({
        failure_type: 'sn_format',
        mail_message_id: mailMessageId1,
        notification_status: 'exception',
        notification_type: 'snail',
        res_partner_id: resPartnerId1,
    });
    const { env, openFormView } = await start();
    await openFormView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });
    patchWithCleanup(env.services.action, {
        doAction(action, options) {
            assert.step('do_action');
            assert.strictEqual(
                action,
                'snailmail.snailmail_letter_format_error_action',
                "action should be the one for format error"
            );
            assert.strictEqual(
                options.additionalContext.message_id,
                mailMessageId1,
                "action should have correct message id"
            );
        },
    });

    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a message component"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIconClickable',
        "should display the notification icon container"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIcon',
        "should display the notification icon"
    );
    assert.hasClass(
        document.querySelector('.o_Message_notificationIcon'),
        'fa-paper-plane',
        "icon should represent snailmail"
    );

    await afterNextRender(() => {
        document.querySelector('.o_Message_notificationIconClickable').click();
    });
    assert.verifySteps(
        ['do_action'],
        "should do an action to display the format error dialog"
    );
});

QUnit.test('Missing Required Fields', async function (assert) {
    assert.expect(8);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const mailMessageId1 = pyEnv['mail.message'].create({
        body: 'not empty',
        message_type: 'snailmail',
        res_id: resPartnerId1, // non 0 id, necessary to fetch failure at init
        model: 'res.partner', // not mail.compose.message, necessary to fetch failure at init
    });
    pyEnv['mail.notification'].create({
        failure_type: 'sn_fields',
        mail_message_id: mailMessageId1,
        notification_status: 'exception',
        notification_type: 'snail',
    });
    const snailMailLetterId1 = pyEnv['snailmail.letter'].create({
        message_id: mailMessageId1,
    });

    const { env, openFormView } = await start();
    await openFormView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });
    patchWithCleanup(env.services.action, {
        doAction(action, options) {
            assert.step('do_action');
            assert.strictEqual(
                action,
                'snailmail.snailmail_letter_missing_required_fields_action',
                "action should be the one for missing fields"
            );
            assert.strictEqual(
                options.additionalContext.default_letter_id,
                snailMailLetterId1,
                "action should have correct letter id"
            );
        },
    });

    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a message component"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIconClickable',
        "should display the notification icon container"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIcon',
        "should display the notification icon"
    );
    assert.hasClass(
        document.querySelector('.o_Message_notificationIcon'),
        'fa-paper-plane',
        "icon should represent snailmail"
    );

    await afterNextRender(() => {
        document.querySelector('.o_Message_notificationIconClickable').click();
    });
    assert.verifySteps(
        ['do_action'],
        "an action should be done to display the missing fields dialog"
    );
});

});
});
