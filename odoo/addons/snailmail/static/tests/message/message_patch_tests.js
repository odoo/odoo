/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { makeDeferred, patchWithCleanup } from "@web/../tests/helpers/utils";
import { click, contains } from "@web/../tests/utils";

QUnit.module("message (patch)");

QUnit.test("Sent", async () => {
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
    await click(".o-mail-Message-notification i.fa-paper-plane");
    await contains(".o-snailmail-SnailmailNotificationPopover i.fa-check");
    await contains(".o-snailmail-SnailmailNotificationPopover", { text: "Sent" });
});

QUnit.test("Canceled", async () => {
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
    await click(".o-mail-Message-notification i.fa-paper-plane");
    await contains(".o-snailmail-SnailmailNotificationPopover i.fa-trash-o");
    await contains(".o-snailmail-SnailmailNotificationPopover", { text: "Canceled" });
});

QUnit.test("Pending", async () => {
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
    await click(".o-mail-Message-notification i.fa-paper-plane");
    await contains(".o-snailmail-SnailmailNotificationPopover i.fa-clock-o");
    await contains(".o-snailmail-SnailmailNotificationPopover", { text: "Awaiting Dispatch" });
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
    const def = makeDeferred();
    const { openFormView } = await start({
        async mockRPC(route, args) {
            if (
                args.method === "cancel_letter" &&
                args.model === "mail.message" &&
                args.args[0][0] === messageId
            ) {
                assert.step(args.method);
                def.resolve();
            }
        },
    });
    await openFormView("res.partner", partnerId);
    await click(".o-mail-Message-notification i.fa-paper-plane");
    await contains(".o-snailmail-SnailmailError .modal-body", {
        text: "The country to which you want to send the letter is not supported by our service.",
    });
    await click("button", { text: "Cancel letter" });
    await contains(".o-snailmail-SnailmailError", { count: 0 });
    await def;
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
    const def = makeDeferred();
    const { openFormView } = await start({
        async mockRPC(route, args) {
            if (
                args.method === "send_letter" &&
                args.model === "mail.message" &&
                args.args[0][0] === messageId
            ) {
                assert.step(args.method);
                def.resolve();
            }
        },
    });
    await openFormView("res.partner", partnerId);
    await click(".o-mail-Message-notification i.fa-paper-plane");
    await contains(".o-snailmail-SnailmailError p", {
        text: "The letter could not be sent due to insufficient credits on your IAP account.",
    });
    await contains("button", { text: "Cancel letter" });
    await click("button", { text: "Re-send letter" });
    await contains(".o-snailmail-SnailmailError", { count: 0 });
    await def;
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
    const def = makeDeferred();
    const { openFormView } = await start({
        async mockRPC(route, args) {
            if (
                args.method === "send_letter" &&
                args.model === "mail.message" &&
                args.args[0][0] === messageId
            ) {
                assert.step(args.method);
                def.resolve();
            }
        },
    });
    await openFormView("res.partner", partnerId);
    await click(".o-mail-Message-notification i.fa-paper-plane");
    await contains(".o-snailmail-SnailmailError p", {
        text: "You need credits on your IAP account to send a letter.",
    });
    await contains("button", { text: "Cancel letter" });
    await click("button", { text: "Re-send letter" });
    await contains(".o-snailmail-SnailmailError", { count: 0 });
    await def;
    assert.verifySteps(["send_letter"]);
});

QUnit.test("Format Error", async (assert) => {
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
    const def = makeDeferred();
    patchWithCleanup(env.services.action, {
        doAction(action, options) {
            assert.step("do_action");
            assert.strictEqual(action, "snailmail.snailmail_letter_format_error_action");
            assert.strictEqual(options.additionalContext.message_id, messageId);
            def.resolve();
        },
    });
    await click(".o-mail-Message-notification i.fa-paper-plane");
    await def;
    assert.verifySteps(["do_action"]);
});

QUnit.test("Missing Required Fields", async (assert) => {
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
    const def = makeDeferred();
    patchWithCleanup(env.services.action, {
        doAction(action, options) {
            assert.step("do_action");
            assert.strictEqual(action, "snailmail.snailmail_letter_missing_required_fields_action");
            assert.strictEqual(options.additionalContext.default_letter_id, snailMailLetterId1);
            def.resolve();
        },
    });
    await click(".o-mail-Message-notification i.fa-paper-plane");
    await def;
    assert.verifySteps(["do_action"]);
});
