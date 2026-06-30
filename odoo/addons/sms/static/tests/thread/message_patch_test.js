/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { makeDeferred, patchWithCleanup } from "@web/../tests/helpers/utils";
import { click, contains } from "@web/../tests/utils";

QUnit.module("message (patch)");

QUnit.test("Notification Processing", async (assert) => {
    const { partnerId } = await _prepareSmsNotification("process");
    const { openFormView } = await start();
    await openFormView("res.partner", partnerId);
    await _assertContainsSmsNotification(assert);
    await _assertContainsPopoverWithIcon(assert, "fa-hourglass-half");
});

QUnit.test("Notification Pending", async (assert) => {
    const { partnerId } = await _prepareSmsNotification("pending");
    const { openFormView } = await start();
    await openFormView("res.partner", partnerId);
    await _assertContainsSmsNotification(assert);
    await _assertContainsPopoverWithIcon(assert, "fa-paper-plane-o");
});

QUnit.test("Notification Sent", async (assert) => {
    const { partnerId } = await _prepareSmsNotification("sent");
    const { openFormView } = await start();
    await openFormView("res.partner", partnerId);
    await _assertContainsPopoverWithIcon(assert, "fa-check");
});

QUnit.test("Notification Error", async (assert) => {
    const openResendActionDef = makeDeferred();
    const { partnerId, messageId } = await _prepareSmsNotification("exception");
    const { env, openFormView } = await start();
    await openFormView("res.partner", partnerId);
    patchWithCleanup(env.services.action, {
        doAction(action, options) {
            assert.strictEqual(action, "sms.sms_resend_action");
            assert.strictEqual(options.additionalContext.default_mail_message_id, messageId);
            assert.step("do_action");
            openResendActionDef.resolve();
        },
    });
    await _assertContainsSmsNotification(assert);
    await click(".o-mail-Message-notification");
    await openResendActionDef;
    assert.verifySteps(["do_action"]);
});

const _prepareSmsNotification = async (notification_status) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Someone", partner_share: true });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "sms",
        model: "res.partner",
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: notification_status,
        notification_type: "sms",
        res_partner_id: partnerId,
    });
    return { partnerId, messageId };
};

const _assertContainsSmsNotification = async (assert) => {
    await contains(".o-mail-Message");
    await contains(".o-mail-Message-notification");
    await contains(".o-mail-Message-notification i");
    assert.hasClass($(".o-mail-Message-notification i"), "fa-mobile");
};

const _assertContainsPopoverWithIcon = async (assert, iconClassName) => {
    await click(".o-mail-Message-notification");
    await contains(".o-mail-MessageNotificationPopover");
    await contains(".o-mail-MessageNotificationPopover i");
    assert.hasClass($(".o-mail-MessageNotificationPopover i"), iconClassName);
    await contains(".o-mail-MessageNotificationPopover", { text: "Someone" });
};
