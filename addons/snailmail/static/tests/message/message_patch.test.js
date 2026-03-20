import {
    click,
    contains,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
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
    await start();
    await openFormView("res.partner", partnerId);
    await click(".o-mail-Message-notification i.fa-paper-plane");
    await contains(".o-snailmail-SnailmailNotificationPopover", {
        text: "(Country Not Supported)",
    });
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
    await start();
    await openFormView("res.partner", partnerId);
    await click(".o-mail-Message-notification i.fa-paper-plane");
    await contains(".o-snailmail-SnailmailNotificationPopover", {
        text: "(Insufficient Credits)",
    });
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
    await start();
    await openFormView("res.partner", partnerId);
    await click(".o-mail-Message-notification i.fa-paper-plane");
    await contains(".o-snailmail-SnailmailNotificationPopover", {
        text: "(No IAP Credits)",
    });
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
    await click(".o-mail-Message-notification i.fa-paper-plane");
    await contains(".o-snailmail-SnailmailNotificationPopover", {
        text: "(Format Error)",
    });
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
    await start();
    await openFormView("res.partner", partnerId);
    await click(".o-mail-Message-notification i.fa-paper-plane");
    await contains(".o-snailmail-SnailmailNotificationPopover", {
        text: "(Missing Required Fields)",
    });
});
