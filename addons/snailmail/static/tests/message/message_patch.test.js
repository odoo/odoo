import {
    assertSteps,
    click,
    contains,
    openFormView,
    start,
    startServer,
    step,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { Deferred } from "@odoo/hoot-mock";
import { getService, onRpc } from "@web/../tests/web_test_helpers";
import { defineSnailmailModels } from "../snailmail_test_helpers";

describe.current.tags("desktop");
defineSnailmailModels();

test("Sent", async () => {
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
    await start();
    await openFormView("res.partner", partnerId);
    await click(".o-mail-Message-notification i.fa-paper-plane");
    await contains(".o-snailmail-SnailmailNotificationPopover i.fa-check");
    await contains(".o-snailmail-SnailmailNotificationPopover", { text: "Sent" });
});

test("Cancelled", async () => {
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
    await start();
    await openFormView("res.partner", partnerId);
    await click(".o-mail-Message-notification i.fa-paper-plane");
    await contains(".o-snailmail-SnailmailNotificationPopover i.fa-trash-o");
    await contains(".o-snailmail-SnailmailNotificationPopover", { text: "Cancelled" });
});

test("Pending", async () => {
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
    await start();
    await openFormView("res.partner", partnerId);
    await click(".o-mail-Message-notification i.fa-paper-plane");
    await contains(".o-snailmail-SnailmailNotificationPopover i.fa-clock-o");
    await contains(".o-snailmail-SnailmailNotificationPopover", { text: "Awaiting Dispatch" });
});

test("No Price Available", async () => {
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
    const def = new Deferred();
    onRpc("mail.message", "cancel_letter", (args) => {
        if (args.args[0][0] === messageId) {
            step(args.method);
            def.resolve();
        }
        return true;
    });
    await start();
    await openFormView("res.partner", partnerId);
    await click(".o-mail-Message-notification i.fa-paper-plane");
    await contains(".o-snailmail-SnailmailError .modal-body", {
        text: "The country to which you want to send the letter is not supported by our service.",
    });
    await click("button", { text: "Cancel letter" });
    await contains(".o-snailmail-SnailmailError", { count: 0 });
    await def;
    assertSteps(["cancel_letter"]);
});

test("Credit Error", async () => {
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
    const def = new Deferred();
    onRpc("mail.message", "send_letter", (args) => {
        if (args.args[0][0] === messageId) {
            step(args.method);
            def.resolve();
        }
        return true;
    });
    await start();
    await openFormView("res.partner", partnerId);
    await click(".o-mail-Message-notification i.fa-paper-plane");
    await contains(".o-snailmail-SnailmailError p", {
        text: "The letter could not be sent due to insufficient credits on your IAP account.",
    });
    await contains("button", { text: "Cancel letter" });
    await click("button", { text: "Re-send letter" });
    await contains(".o-snailmail-SnailmailError", { count: 0 });
    await def;
    assertSteps(["send_letter"]);
});

test("Trial Error", async () => {
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
    const def = new Deferred();
    onRpc("mail.message", "send_letter", (args) => {
        if (args.args[0][0] === messageId) {
            step(args.method);
            def.resolve();
        }
        return true;
    });
    await start();
    await openFormView("res.partner", partnerId);
    await click(".o-mail-Message-notification i.fa-paper-plane");
    await contains(".o-snailmail-SnailmailError p", {
        text: "You need credits on your IAP account to send a letter.",
    });
    await contains("button", { text: "Cancel letter" });
    await click("button", { text: "Re-send letter" });
    await contains(".o-snailmail-SnailmailError", { count: 0 });
    await def;
    assertSteps(["send_letter"]);
});

test("Format Error", async () => {
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
    await start();
    await openFormView("res.partner", partnerId);
    getService("action").doAction = (action, options) => {
        step("do_action");
        expect(action).toBe("snailmail.snailmail_letter_format_error_action");
        expect(options.additionalContext.message_id).toBe(messageId);
        def.resolve();
    };
    const def = new Deferred();
    await click(".o-mail-Message-notification i.fa-paper-plane");
    await def;
    assertSteps(["do_action"]);
});

test("Missing Required Fields", async () => {
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
    await start();
    await openFormView("res.partner", partnerId);
    getService("action").doAction = (action, options) => {
        step("do_action");
        expect(action).toBe("snailmail.snailmail_letter_missing_required_fields_action");
        expect(options?.additionalContext.default_letter_id).toBe(snailMailLetterId1);
        def.resolve();
    };
    const def = new Deferred();
    await click(".o-mail-Message-notification i.fa-paper-plane");
    await def;
    assertSteps(["do_action"]);
});
