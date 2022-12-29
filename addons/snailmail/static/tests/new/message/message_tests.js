/** @odoo-module **/

import { start, startServer, click } from "@mail/../tests/helpers/test_utils";
import { makeDeferred, patchWithCleanup } from "@web/../tests/helpers/utils";

QUnit.module("snail message");

QUnit.test("Sent", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Someone",
        partner_share: true,
    });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "snailmail",
        model: "res.partner",
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "snail",
        res_partner_id: partnerId,
    });
    const { openFormView } = await start();
    await openFormView("res.partner", partnerId);
    assert.containsOnce($, ".o-mail-Message");
    assert.containsOnce($, ".o-mail-Message-notification");
    assert.containsOnce($, ".o-mail-Message-notification i");
    assert.hasClass($(".o-mail-Message-notification i"), "fa-paper-plane");

    await click(".o-mail-Message-notification");
    assert.containsOnce($, ".o-snailmail-SnailmailNotificationPopover");
    assert.containsOnce($, ".o-snailmail-SnailmailNotificationPopover i");
    assert.hasClass($(".o-snailmail-SnailmailNotificationPopover i"), "fa-check");
    assert.strictEqual($(".o-snailmail-SnailmailNotificationPopover").text(), "Sent");
});

QUnit.test("Canceled", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Someone",
        partner_share: true,
    });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "snailmail",
        model: "res.partner",
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "canceled",
        notification_type: "snail",
        res_partner_id: partnerId,
    });
    const { openFormView } = await start();
    await openFormView("res.partner", partnerId);
    assert.containsOnce($, ".o-mail-Message");
    assert.containsOnce($, ".o-mail-Message-notification");
    assert.containsOnce($, ".o-mail-Message-notification i");
    assert.hasClass($(".o-mail-Message-notification i"), "fa-paper-plane");

    await click(".o-mail-Message-notification");
    assert.containsOnce($, ".o-snailmail-SnailmailNotificationPopover");
    assert.containsOnce($, ".o-snailmail-SnailmailNotificationPopover i");
    assert.hasClass($(".o-snailmail-SnailmailNotificationPopover i"), "fa-trash-o");
    assert.strictEqual($(".o-snailmail-SnailmailNotificationPopover").text(), "Canceled");
});

QUnit.test("Pending", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Someone",
        partner_share: true,
    });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "snailmail",
        model: "res.partner",
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "ready",
        notification_type: "snail",
        res_partner_id: partnerId,
    });
    const { openFormView } = await start();
    await openFormView("res.partner", partnerId);
    assert.containsOnce($, ".o-mail-Message");
    assert.containsOnce($, ".o-mail-Message-notification");
    assert.containsOnce($, ".o-mail-Message-notification i");
    assert.hasClass($(".o-mail-Message-notification i"), "fa-paper-plane");

    await click(".o-mail-Message-notification");
    assert.containsOnce($, ".o-snailmail-SnailmailNotificationPopover");
    assert.containsOnce($, ".o-snailmail-SnailmailNotificationPopover i");
    assert.hasClass($(".o-snailmail-SnailmailNotificationPopover i"), "fa-clock-o");
    assert.strictEqual($(".o-snailmail-SnailmailNotificationPopover").text(), "Awaiting Dispatch");
});

QUnit.test("No Price Available", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Someone",
        partner_share: true,
    });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "snailmail",
        model: "res.partner",
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        failure_type: "sn_price",
        mail_message_id: messageId,
        notification_status: "exception",
        notification_type: "snail",
        res_partner_id: partnerId,
    });
    const { openFormView } = await start({
        async mockRPC(route, args) {
            if (
                args.method === "cancel_letter" &&
                args.model === "mail.message" &&
                args.args[0][0] === messageId
            ) {
                assert.step(args.method);
            }
        },
    });
    await openFormView("res.partner", partnerId);
    assert.containsOnce($, ".o-mail-Message");
    assert.containsOnce($, ".o-mail-Message-notification");
    assert.containsOnce($, ".o-mail-Message-notification i");
    assert.hasClass($(".o-mail-Message-notification i"), "fa-paper-plane");

    await click(".o-mail-Message-notification");
    assert.containsOnce($, ".o-snailmail-SnailmailError");
    assert.strictEqual(
        $(".o-snailmail-SnailmailError .modal-body").text().trim(),
        "The country to which you want to send the letter is not supported by our service."
    );
    assert.containsOnce($, "button:contains(Cancel letter)");
    await click("button:contains(Cancel letter)");
    assert.containsNone($, ".o-snailmail-SnailmailError");
    assert.verifySteps(["cancel_letter"]);
});

QUnit.test("Credit Error", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Someone",
        partner_share: true,
    });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "snailmail",
        model: "res.partner",
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        failure_type: "sn_credit",
        mail_message_id: messageId,
        notification_status: "exception",
        notification_type: "snail",
        res_partner_id: partnerId,
    });
    const { openFormView } = await start({
        async mockRPC(route, args) {
            if (
                args.method === "send_letter" &&
                args.model === "mail.message" &&
                args.args[0][0] === messageId
            ) {
                assert.step(args.method);
            }
        },
    });
    await openFormView("res.partner", partnerId);
    assert.containsOnce($, ".o-mail-Message");
    assert.containsOnce($, ".o-mail-Message-notification");
    assert.containsOnce($, ".o-mail-Message-notification i");
    assert.hasClass($(".o-mail-Message-notification i"), "fa-paper-plane");

    await click(".o-mail-Message-notification");
    assert.containsOnce($, ".o-snailmail-SnailmailError");
    assert.strictEqual(
        $(".o-snailmail-SnailmailError p").text().trim(),
        "The letter could not be sent due to insufficient credits on your IAP account."
    );
    assert.containsOnce($, "button:contains(Re-send letter)");
    assert.containsOnce($, "button:contains(Cancel letter)");
    await click("button:contains(Re-send letter)");
    assert.containsNone($, ".o-snailmail-SnailmailError");
    assert.verifySteps(["send_letter"]);
});

QUnit.test("Trial Error", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Someone",
        partner_share: true,
    });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "snailmail",
        model: "res.partner",
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        failure_type: "sn_trial",
        mail_message_id: messageId,
        notification_status: "exception",
        notification_type: "snail",
        res_partner_id: partnerId,
    });
    const { openFormView } = await start({
        async mockRPC(route, args) {
            if (
                args.method === "send_letter" &&
                args.model === "mail.message" &&
                args.args[0][0] === messageId
            ) {
                assert.step(args.method);
            }
        },
    });
    await openFormView("res.partner", partnerId);
    assert.containsOnce($, ".o-mail-Message");
    assert.containsOnce($, ".o-mail-Message-notification");
    assert.containsOnce($, ".o-mail-Message-notification i");
    assert.hasClass($(".o-mail-Message-notification i"), "fa-paper-plane");

    await click(".o-mail-Message-notification");
    assert.containsOnce($, ".o-snailmail-SnailmailError");
    assert.strictEqual(
        $(".o-snailmail-SnailmailError p").text().trim(),
        "You need credits on your IAP account to send a letter."
    );
    assert.containsOnce($, "button:contains(Re-send letter)");
    assert.containsOnce($, "button:contains(Cancel letter)");
    await click("button:contains(Re-send letter)");
    assert.containsNone($, ".o-snailmail-SnailmailError");
    assert.verifySteps(["send_letter"]);
});

QUnit.test("Format Error", async (assert) => {
    const openFormatErrorActionDef = makeDeferred();
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Someone",
        partner_share: true,
    });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "snailmail",
        model: "res.partner",
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        failure_type: "sn_format",
        mail_message_id: messageId,
        notification_status: "exception",
        notification_type: "snail",
        res_partner_id: partnerId,
    });
    const { env, openFormView } = await start();
    await openFormView("res.partner", partnerId);
    patchWithCleanup(env.services.action, {
        doAction(action, options) {
            assert.step("do_action");
            assert.strictEqual(action, "snailmail.snailmail_letter_format_error_action");
            assert.strictEqual(options.additionalContext.message_id, messageId);
            openFormatErrorActionDef.resolve();
        },
    });
    assert.containsOnce($, ".o-mail-Message");
    assert.containsOnce($, ".o-mail-Message-notification");
    assert.containsOnce($, ".o-mail-Message-notification i");
    assert.hasClass($(".o-mail-Message-notification i"), "fa-paper-plane");

    click(".o-mail-Message-notification").then(() => {});
    await openFormatErrorActionDef;
    assert.verifySteps(["do_action"]);
});

QUnit.test("Missing Required Fields", async (assert) => {
    const openRequiredFieldsActionDef = makeDeferred();
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "snailmail",
        res_id: partnerId,
        model: "res.partner",
    });
    pyEnv["mail.notification"].create({
        failure_type: "sn_fields",
        mail_message_id: messageId,
        notification_status: "exception",
        notification_type: "snail",
    });
    const snailMailLetterId1 = pyEnv["snailmail.letter"].create({
        message_id: messageId,
    });
    const { env, openFormView } = await start();
    await openFormView("res.partner", partnerId);
    patchWithCleanup(env.services.action, {
        doAction(action, options) {
            assert.step("do_action");
            assert.strictEqual(action, "snailmail.snailmail_letter_missing_required_fields_action");
            assert.strictEqual(options.additionalContext.default_letter_id, snailMailLetterId1);
            openRequiredFieldsActionDef.resolve();
        },
    });
    assert.containsOnce($, ".o-mail-Message");
    assert.containsOnce($, ".o-mail-Message-notification");
    assert.containsOnce($, ".o-mail-Message-notification i");
    assert.hasClass($(".o-mail-Message-notification i"), "fa-paper-plane");

    click(".o-mail-Message-notification").then(() => {});
    await openRequiredFieldsActionDef;
    assert.verifySteps(["do_action"]);
});
