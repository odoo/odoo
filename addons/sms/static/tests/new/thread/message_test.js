/** @odoo-module **/

import { startServer, start, click } from "@mail/../tests/helpers/test_utils";
import { getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeDeferred } from "@mail/utils/deferred";

let target;

QUnit.module("sms_message", {
    async beforeEach() {
        target = getFixture();
    },
});

QUnit.test("Notification Sent", async function (assert) {
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv["res.partner"].create({ name: "Someone", partner_share: true });
    const mailMessageId1 = pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "sms",
        model: "res.partner",
        res_id: resPartnerId1,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: mailMessageId1,
        notification_status: "sent",
        notification_type: "sms",
        res_partner_id: resPartnerId1,
    });
    const { openFormView } = await start();
    await openFormView("res.partner", resPartnerId1);
    assert.containsOnce(target, ".o-mail-message");
    assert.containsOnce(target, ".o-mail-message-notification-icon-clickable");
    assert.containsOnce(target, ".o-mail-message-notification-icon");
    assert.hasClass(target.querySelector(".o-mail-message-notification-icon"), "fa-mobile");

    await click(".o-mail-message-notification-icon-clickable");
    assert.containsOnce(target, ".o-mail-message-notification-popover");
    assert.containsOnce(target, ".o-mail-message-notification-popover-icon");
    assert.hasClass(target.querySelector(".o-mail-message-notification-popover-icon"), "fa-check");
    assert.containsOnce(target, ".o-mail-message-notification-popover-partner-name");
    assert.strictEqual(
        target
            .querySelector(".o-mail-message-notification-popover-partner-name")
            .textContent.trim(),
        "Someone"
    );
});

QUnit.test("Notification Error", async function (assert) {
    const openResendActionDef = makeDeferred();
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv["res.partner"].create({ name: "Someone", partner_share: true });
    const mailMessageId1 = pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "sms",
        model: "res.partner",
        res_id: resPartnerId1,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: mailMessageId1,
        notification_status: "exception",
        notification_type: "sms",
        res_partner_id: resPartnerId1,
    });
    const { env, openFormView } = await start();
    await openFormView("res.partner", resPartnerId1);
    patchWithCleanup(env.services.action, {
        doAction(action, options) {
            assert.step("do_action");
            assert.strictEqual(action, "sms.sms_resend_action");
            assert.strictEqual(options.additionalContext.default_mail_message_id, mailMessageId1);
            openResendActionDef.resolve();
        },
    });

    assert.containsOnce(target, ".o-mail-message");
    assert.containsOnce(target, ".o-mail-message-notification-icon-clickable");
    assert.containsOnce(target, ".o-mail-message-notification-icon");
    assert.hasClass(target.querySelector(".o-mail-message-notification-icon"), "fa-mobile");
    click(".o-mail-message-notification-icon-clickable").catch(() => {});
    await openResendActionDef;
    assert.verifySteps(["do_action"]);
});
