/** @odoo-module **/

import { insert, insertAndReplace } from '@mail/model/model_field_command';
import { makeDeferred } from '@mail/utils/deferred';
import {
    afterNextRender,
    beforeEach,
    start,
} from '@mail/../tests/helpers/test_utils';

import Bus from 'web.Bus';

QUnit.module('sms', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('message_tests.js', {
    async beforeEach() {
        await beforeEach(this);
    },
});

QUnit.test('Notification Sent', async function (assert) {
    assert.expect(9);

    this.data['res.partner'].records.push({ id: 12, name: "Someone", partner_share: true });
    this.data['mail.channel'].records.push({ id: 11 });
    this.data['mail.message'].records.push({
        body: 'not empty',
        id: 10,
        message_type: 'sms',
        model: 'mail.channel',
        res_id: 11,
    });
    this.data['mail.notification'].records.push({
        id: 11,
        mail_message_id: 10,
        notification_status: 'sent',
        notification_type: 'sms',
        res_partner_id: 12,
    });
    const { createThreadViewComponent, messaging } = await start({ data: this.data });
    const threadViewer = messaging.models['ThreadViewer'].create({
        hasThreadView: true,
        qunitTest: insertAndReplace(),
        thread: insert({
            id: 11,
            model: 'mail.channel',
        }),
    });
    await createThreadViewComponent(threadViewer.threadView);

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
        'fa-mobile',
        "icon should represent sms"
    );

    await afterNextRender(() => {
        document.querySelector('.o_Message_notificationIconClickable').click();
    });
    assert.containsOnce(
        document.body,
        '.o_NotificationPopover',
        "notification popover should be open"
    );
    assert.containsOnce(
        document.body,
        '.o_NotificationPopover_notificationIcon',
        "popover should have one icon"
    );
    assert.hasClass(
        document.querySelector('.o_NotificationPopover_notificationIcon'),
        'fa-check',
        "popover should have the sent icon"
    );
    assert.containsOnce(
        document.body,
        '.o_NotificationPopover_notificationPartnerName',
        "popover should have the partner name"
    );
    assert.strictEqual(
        document.querySelector('.o_NotificationPopover_notificationPartnerName').textContent.trim(),
        "Someone",
        "partner name should be correct"
    );
});

QUnit.test('Notification Error', async function (assert) {
    assert.expect(8);

    const openResendActionDef = makeDeferred();
    const bus = new Bus();
    bus.on('do-action', null, payload => {
        assert.step('do_action');
        assert.strictEqual(
            payload.action,
            'sms.sms_resend_action',
            "action should be the one to resend sms"
        );
        assert.strictEqual(
            payload.options.additional_context.default_mail_message_id,
            10,
            "action should have correct message id"
        );
        openResendActionDef.resolve();
    });
    this.data['res.partner'].records.push({ id: 12, name: "Someone", partner_share: true });
    this.data['mail.channel'].records.push({ id: 11 });
    this.data['mail.message'].records.push({
        body: 'not empty',
        id: 10,
        message_type: 'sms',
        model: 'mail.channel',
        res_id: 11,
    });
    this.data['mail.notification'].records.push({
        id: 11,
        mail_message_id: 10,
        notification_status: 'exception',
        notification_type: 'sms',
        res_partner_id: 12,
    });
    const { createThreadViewComponent, messaging } = await start({ data: this.data, env: { bus } });
    const threadViewer = messaging.models['ThreadViewer'].create({
        hasThreadView: true,
        qunitTest: insertAndReplace(),
        thread: insert({
            id: 11,
            model: 'mail.channel',
        }),
    });
    await createThreadViewComponent(threadViewer.threadView);

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
        'fa-mobile',
        "icon should represent sms"
    );
    document.querySelector('.o_Message_notificationIconClickable').click();
    await openResendActionDef;
    assert.verifySteps(
        ['do_action'],
        "should do an action to display the resend sms dialog"
    );
});

});
});
