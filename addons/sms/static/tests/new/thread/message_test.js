/** @odoo-module **/

import { startServer, start, click } from "@mail/../tests/helpers/test_utils";
import { makeDeferred, patchWithCleanup } from "@web/../tests/helpers/utils";

QUnit.module("sms_message");

QUnit.test("Notification Sent", async function (assert) {
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
    await openFormView("res.partner", partnerId);
    assert.containsOnce($, ".o-mail-Message");
    assert.containsOnce($, ".o-mail-Message-notification");
    assert.containsOnce($, ".o-mail-Message-notification i");
    assert.hasClass($(".o-mail-Message-notification i"), "fa-mobile");

    await click(".o-mail-Message-notification");
    assert.containsOnce($, ".o-mail-MessageNotificationPopover");
    assert.containsOnce($, ".o-mail-MessageNotificationPopover i");
    assert.hasClass($(".o-mail-MessageNotificationPopover i"), "fa-check");
    assert.containsOnce($, ".o-mail-MessageNotificationPopover:contains(Someone)");
});

QUnit.test("Notification Error", async function (assert) {
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
    await openFormView("res.partner", partnerId);
    patchWithCleanup(env.services.action, {
        doAction(action, options) {
            assert.step("do_action");
            assert.strictEqual(action, "sms.sms_resend_action");
            assert.strictEqual(options.additionalContext.default_mail_message_id, messageId);
            openResendActionDef.resolve();
        },
    });

    assert.containsOnce($, ".o-mail-Message");
    assert.containsOnce($, ".o-mail-Message-notification");
    assert.containsOnce($, ".o-mail-Message-notification i");
    assert.hasClass($(".o-mail-Message-notification i"), "fa-mobile");
    click(".o-mail-Message-notification").catch(() => {});
    await openResendActionDef;
    assert.verifySteps(["do_action"]);
});
