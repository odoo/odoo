/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";
import { makeDeferred } from "@mail/utils/deferred";

import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { click, contains } from "@web/../tests/utils";

QUnit.module("snailmail", {}, function () {
QUnit.module("components", {}, async function () {
QUnit.module("message_tests.js");

QUnit.test("Sent", async function () {
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv["res.partner"].create({
        name: "Someone",
        partner_share: true,
    });
    const mailMessageId1 = pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "snailmail",
        model: "res.partner",
        res_id: resPartnerId1,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: mailMessageId1,
        notification_status: "sent",
        notification_type: "snail",
        res_partner_id: resPartnerId1,
    });
    const { openFormView } = await start();
    await openFormView({
        res_id: resPartnerId1,
        res_model: "res.partner",
    });
    await contains(".o_Message");
    await contains(".o_Message_notificationIcon.fa-paper-plane");
    await click(".o_Message_notificationIconClickable");
    await contains(".o_SnailmailNotificationPopoverContentView", { text: "Sent" });
    await contains(".o_SnailmailNotificationPopoverContentView_icon.fa-check");
});

QUnit.test("Canceled", async function () {
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv["res.partner"].create({
        name: "Someone",
        partner_share: true,
    });
    const mailMessageId1 = pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "snailmail",
        model: "res.partner",
        res_id: resPartnerId1,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: mailMessageId1,
        notification_status: "canceled",
        notification_type: "snail",
        res_partner_id: resPartnerId1,
    });
    const { openFormView } = await start();
    await openFormView({
        res_id: resPartnerId1,
        res_model: "res.partner",
    });
    await contains(".o_Message");
    await contains(".o_Message_notificationIcon.fa-paper-plane");
    await click(".o_Message_notificationIconClickable");
    await contains(".o_SnailmailNotificationPopoverContentView", { text: "Canceled" });
    await contains(".o_SnailmailNotificationPopoverContentView_icon.fa-trash-o");
});

QUnit.test("Pending", async function () {
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv["res.partner"].create({
        name: "Someone",
        partner_share: true,
    });
    const mailMessageId1 = pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "snailmail",
        model: "res.partner",
        res_id: resPartnerId1,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: mailMessageId1,
        notification_status: "ready",
        notification_type: "snail",
        res_partner_id: resPartnerId1,
    });
    const { openFormView } = await start();
    await openFormView({
        res_id: resPartnerId1,
        res_model: "res.partner",
    });
    await contains(".o_Message");
    await contains(".o_Message_notificationIcon.fa-paper-plane");
    await click(".o_Message_notificationIconClickable");
    await contains(".o_SnailmailNotificationPopoverContentView", {
        text: "Awaiting Dispatch",
    });
    await contains(".o_SnailmailNotificationPopoverContentView_icon.fa-clock-o");
});

QUnit.test("No Price Available", async function (assert) {
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv["res.partner"].create({
        name: "Someone",
        partner_share: true,
    });
    const mailMessageId1 = pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "snailmail",
        model: "res.partner",
        res_id: resPartnerId1,
    });
    pyEnv["mail.notification"].create({
        failure_type: "sn_price",
        mail_message_id: mailMessageId1,
        notification_status: "exception",
        notification_type: "snail",
        res_partner_id: resPartnerId1,
    });
    const def = makeDeferred();
    const { openFormView } = await start({
        async mockRPC(route, args) {
            if (
                args.method === "cancel_letter" &&
                args.model === "mail.message" &&
                args.args[0][0] === mailMessageId1
            ) {
                assert.step(args.method);
                def.resolve();
            }
        },
    });
    await openFormView({
        res_id: resPartnerId1,
        res_model: "res.partner",
    });
    await contains(".o_Message");
    await contains(".o_Message_notificationIcon.fa-paper-plane");
    await click(".o_Message_notificationIconClickable");
    await contains(".o_SnailmailError");
    await contains(".o_SnailmailError_contentPrice");
    await click(".o_SnailmailError_cancelLetterButton");
    await contains(".o_SnailmailError", { count: 0 });
    await def;
    assert.verifySteps(["cancel_letter"], "should have made a RPC call to 'cancel_letter'");
});

QUnit.test("Credit Error", async function (assert) {
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv["res.partner"].create({
        name: "Someone",
        partner_share: true,
    });
    const mailMessageId1 = pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "snailmail",
        model: "res.partner",
        res_id: resPartnerId1,
    });
    pyEnv["mail.notification"].create({
        failure_type: "sn_credit",
        mail_message_id: mailMessageId1,
        notification_status: "exception",
        notification_type: "snail",
        res_partner_id: resPartnerId1,
    });
    const def = makeDeferred();
    const { openFormView } = await start({
        async mockRPC(route, args) {
            if (
                args.method === "send_letter" &&
                args.model === "mail.message" &&
                args.args[0][0] === mailMessageId1
            ) {
                assert.step(args.method);
                def.resolve();
            }
        },
    });
    await openFormView({
        res_id: resPartnerId1,
        res_model: "res.partner",
    });
    await contains(".o_Message");
    await contains(".o_Message_notificationIcon.fa-paper-plane");
    await click(".o_Message_notificationIconClickable");
    await contains(".o_SnailmailError");
    await contains(".o_SnailmailError_contentCredit");
    await contains(".o_SnailmailError_cancelLetterButton");
    await click(".o_SnailmailError_resendLetterButton");
    await contains(".o_SnailmailError", { count: 0 });
    await def;
    assert.verifySteps(["send_letter"], "should have made a RPC call to 'send_letter'");
});

QUnit.test("Trial Error", async function (assert) {
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv["res.partner"].create({
        name: "Someone",
        partner_share: true,
    });
    const mailMessageId1 = pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "snailmail",
        model: "res.partner",
        res_id: resPartnerId1,
    });
    pyEnv["mail.notification"].create({
        failure_type: "sn_trial",
        mail_message_id: mailMessageId1,
        notification_status: "exception",
        notification_type: "snail",
        res_partner_id: resPartnerId1,
    });
    const def = makeDeferred();
    const { openFormView } = await start({
        async mockRPC(route, args) {
            if (
                args.method === "send_letter" &&
                args.model === "mail.message" &&
                args.args[0][0] === mailMessageId1
            ) {
                assert.step(args.method);
                def.resolve();
            }
        },
    });
    await openFormView({
        res_id: resPartnerId1,
        res_model: "res.partner",
    });
    await contains(".o_Message");
    await contains(".o_Message_notificationIcon.fa-paper-plane");
    await click(".o_Message_notificationIconClickable");
    await contains(".o_SnailmailError");
    await contains(".o_SnailmailError_contentTrial");
    await contains(".o_SnailmailError_cancelLetterButton");
    await click(".o_SnailmailError_resendLetterButton");
    await contains(".o_SnailmailError", { count: 0 });
    await def;
    assert.verifySteps(["send_letter"], "should have made a RPC call to 'send_letter'");
});

QUnit.test("Format Error", async function (assert) {
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv["res.partner"].create({
        name: "Someone",
        partner_share: true,
    });
    const mailMessageId1 = pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "snailmail",
        model: "res.partner",
        res_id: resPartnerId1,
    });
    pyEnv["mail.notification"].create({
        failure_type: "sn_format",
        mail_message_id: mailMessageId1,
        notification_status: "exception",
        notification_type: "snail",
        res_partner_id: resPartnerId1,
    });
    const { env, openFormView } = await start();
    await openFormView({
        res_id: resPartnerId1,
        res_model: "res.partner",
    });
    const def = makeDeferred();
    patchWithCleanup(env.services.action, {
        doAction(action, options) {
            assert.step("do_action");
            assert.strictEqual(
                action,
                "snailmail.snailmail_letter_format_error_action",
                "action should be the one for format error"
            );
            assert.strictEqual(
                options.additionalContext.message_id,
                mailMessageId1,
                "action should have correct message id"
            );
            def.resolve();
        },
    });
    await contains(".o_Message");
    await contains(".o_Message_notificationIcon.fa-paper-plane");
    await click(".o_Message_notificationIconClickable");
    await def;
    assert.verifySteps(["do_action"], "should do an action to display the format error dialog");
});

QUnit.test("Missing Required Fields", async function (assert) {
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv["res.partner"].create({});
    const mailMessageId1 = pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "snailmail",
        res_id: resPartnerId1, // non 0 id, necessary to fetch failure at init
        model: "res.partner", // not mail.compose.message, necessary to fetch failure at init
    });
    pyEnv["mail.notification"].create({
        failure_type: "sn_fields",
        mail_message_id: mailMessageId1,
        notification_status: "exception",
        notification_type: "snail",
    });
    const snailMailLetterId1 = pyEnv["snailmail.letter"].create({
        message_id: mailMessageId1,
    });

    const { env, openFormView } = await start();
    await openFormView({
        res_id: resPartnerId1,
        res_model: "res.partner",
    });
    const def = makeDeferred();
    patchWithCleanup(env.services.action, {
        doAction(action, options) {
            assert.step("do_action");
            assert.strictEqual(
                action,
                "snailmail.snailmail_letter_missing_required_fields_action",
                "action should be the one for missing fields"
            );
            assert.strictEqual(
                options.additionalContext.default_letter_id,
                snailMailLetterId1,
                "action should have correct letter id"
            );
            def.resolve();
        },
    });
    await contains(".o_Message");
    await contains(".o_Message_notificationIcon.fa-paper-plane");
    await click(".o_Message_notificationIconClickable");
    await def;
    assert.verifySteps(
        ["do_action"],
        "an action should be done to display the missing fields dialog"
    );
});
});
});
