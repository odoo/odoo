/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { makeDeferred, patchWithCleanup } from "@web/../tests/helpers/utils";
import { click, contains } from "@web/../tests/utils";

QUnit.module("message (patch)");

QUnit.test("Notification Sent", async (assert) => {
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
        notification_status: "sent",
        notification_type: "sms",
        res_partner_id: partnerId,
    });
    const { openFormView } = await start();
    openFormView("res.partner", partnerId);
    await contains(".o-mail-Message");
    await contains(".o-mail-Message-notification");
    await contains(".o-mail-Message-notification i");
    assert.hasClass($(".o-mail-Message-notification i"), "fa-mobile");

    await click(".o-mail-Message-notification");
    await contains(".o-mail-MessageNotificationPopover");
    await contains(".o-mail-MessageNotificationPopover i");
    assert.hasClass($(".o-mail-MessageNotificationPopover i"), "fa-check");
    await contains(".o-mail-MessageNotificationPopover", { text: "Someone" });
});

QUnit.test("Notification Error", async (assert) => {
    const openResendActionDef = makeDeferred();
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
        notification_status: "exception",
        notification_type: "sms",
        res_partner_id: partnerId,
    });
    const { env, openFormView } = await start();
    openFormView("res.partner", partnerId);
    patchWithCleanup(env.services.action, {
        doAction(action, options) {
            assert.step("do_action");
            assert.strictEqual(action, "sms.sms_resend_action");
            assert.strictEqual(options.additionalContext.default_mail_message_id, messageId);
            openResendActionDef.resolve();
        },
    });

    await contains(".o-mail-Message");
    await contains(".o-mail-Message-notification");
    await contains(".o-mail-Message-notification i");
    assert.hasClass($(".o-mail-Message-notification i"), "fa-mobile");
    await click(".o-mail-Message-notification");
    await openResendActionDef;
    assert.verifySteps(["do_action"]);
});
