/** @odoo-module **/

import { start, startServer, click } from "@mail/../tests/helpers/test_utils";
import { getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeDeferred } from "@mail/utils/deferred";

let target;

QUnit.module("snail message", {
    async beforeEach() {
        target = getFixture();
    },
});

QUnit.test("Sent", async function (assert) {
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
    await openFormView("res.partner", resPartnerId1);
    assert.containsOnce(target, ".o-mail-message");
    assert.containsOnce(target, ".o-mail-message-notification");
    assert.containsOnce(target, ".o-mail-message-notification i");
    assert.hasClass($(target).find(".o-mail-message-notification i"), "fa-paper-plane");

    await click(".o-mail-message-notification");
    assert.containsOnce(target, ".o-snailmail-notification-popover");
    assert.containsOnce(target, ".o-snailmail-notification-popover i");
    assert.hasClass($(target).find(".o-snailmail-notification-popover i"), "fa-check");
    assert.strictEqual($(target).find(".o-snailmail-notification-popover").text(), "Sent");
});

QUnit.test("Canceled", async function (assert) {
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
    await openFormView("res.partner", resPartnerId1);
    assert.containsOnce(target, ".o-mail-message");
    assert.containsOnce(target, ".o-mail-message-notification");
    assert.containsOnce(target, ".o-mail-message-notification i");
    assert.hasClass($(target).find(".o-mail-message-notification i"), "fa-paper-plane");

    await click(".o-mail-message-notification");
    assert.containsOnce(target, ".o-snailmail-notification-popover");
    assert.containsOnce(target, ".o-snailmail-notification-popover i");
    assert.hasClass($(target).find(".o-snailmail-notification-popover i"), "fa-trash-o");
    assert.strictEqual($(target).find(".o-snailmail-notification-popover").text(), "Canceled");
});

QUnit.test("Pending", async function (assert) {
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
    await openFormView("res.partner", resPartnerId1);
    assert.containsOnce(target, ".o-mail-message");
    assert.containsOnce(target, ".o-mail-message-notification");
    assert.containsOnce(target, ".o-mail-message-notification i");
    assert.hasClass($(target).find(".o-mail-message-notification i"), "fa-paper-plane");

    await click(".o-mail-message-notification");
    assert.containsOnce(target, ".o-snailmail-notification-popover");
    assert.containsOnce(target, ".o-snailmail-notification-popover i");
    assert.hasClass($(target).find(".o-snailmail-notification-popover i"), "fa-clock-o");
    assert.strictEqual(
        $(target).find(".o-snailmail-notification-popover").text(),
        "Awaiting Dispatch"
    );
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
    const { openFormView } = await start({
        async mockRPC(route, args) {
            if (
                args.method === "cancel_letter" &&
                args.model === "mail.message" &&
                args.args[0][0] === mailMessageId1
            ) {
                assert.step(args.method);
            }
        },
    });
    await openFormView("res.partner", resPartnerId1);
    assert.containsOnce(target, ".o-mail-message");
    assert.containsOnce(target, ".o-mail-message-notification");
    assert.containsOnce(target, ".o-mail-message-notification i");
    assert.hasClass($(target).find(".o-mail-message-notification i"), "fa-paper-plane");

    await click(".o-mail-message-notification");
    assert.containsOnce(target, ".o-snailmail-error");
    assert.strictEqual(
        $(target).find(".o-snailmail-error .modal-body").text().trim(),
        "The country to which you want to send the letter is not supported by our service."
    );
    assert.containsOnce(target, "button:contains(Cancel letter)");
    await click("button:contains(Cancel letter)");
    assert.containsNone(target, ".o-snailmail-error");
    assert.verifySteps(["cancel_letter"]);
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
    const { openFormView } = await start({
        async mockRPC(route, args) {
            if (
                args.method === "send_letter" &&
                args.model === "mail.message" &&
                args.args[0][0] === mailMessageId1
            ) {
                assert.step(args.method);
            }
        },
    });
    await openFormView("res.partner", resPartnerId1);
    assert.containsOnce(target, ".o-mail-message");
    assert.containsOnce(target, ".o-mail-message-notification");
    assert.containsOnce(target, ".o-mail-message-notification i");
    assert.hasClass($(target).find(".o-mail-message-notification i"), "fa-paper-plane");

    await click(".o-mail-message-notification");
    assert.containsOnce(target, ".o-snailmail-error");
    assert.strictEqual(
        $(target).find(".o-snailmail-error p").text().trim(),
        "The letter could not be sent due to insufficient credits on your IAP account."
    );
    assert.containsOnce(target, "button:contains(Re-send letter)");
    assert.containsOnce(target, "button:contains(Cancel letter)");
    await click("button:contains(Re-send letter)");
    assert.containsNone(target, ".o-snailmail-error");
    assert.verifySteps(["send_letter"]);
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
    const { openFormView } = await start({
        async mockRPC(route, args) {
            if (
                args.method === "send_letter" &&
                args.model === "mail.message" &&
                args.args[0][0] === mailMessageId1
            ) {
                assert.step(args.method);
            }
        },
    });
    await openFormView("res.partner", resPartnerId1);
    assert.containsOnce(target, ".o-mail-message");
    assert.containsOnce(target, ".o-mail-message-notification");
    assert.containsOnce(target, ".o-mail-message-notification i");
    assert.hasClass($(target).find(".o-mail-message-notification i"), "fa-paper-plane");

    await click(".o-mail-message-notification");
    assert.containsOnce(target, ".o-snailmail-error");
    assert.strictEqual(
        $(target).find(".o-snailmail-error p").text().trim(),
        "You need credits on your IAP account to send a letter."
    );
    assert.containsOnce(target, "button:contains(Re-send letter)");
    assert.containsOnce(target, "button:contains(Cancel letter)");
    await click("button:contains(Re-send letter)");
    assert.containsNone(target, ".o-snailmail-error");
    assert.verifySteps(["send_letter"]);
});

QUnit.test("Format Error", async function (assert) {
    const openFormatErrorActionDef = makeDeferred();
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
    await openFormView("res.partner", resPartnerId1);
    patchWithCleanup(env.services.action, {
        doAction(action, options) {
            assert.step("do_action");
            assert.strictEqual(action, "snailmail.snailmail_letter_format_error_action");
            assert.strictEqual(options.additionalContext.message_id, mailMessageId1);
            openFormatErrorActionDef.resolve();
        },
    });

    assert.containsOnce(target, ".o-mail-message");
    assert.containsOnce(target, ".o-mail-message-notification");
    assert.containsOnce(target, ".o-mail-message-notification i");
    assert.hasClass($(target).find(".o-mail-message-notification i"), "fa-paper-plane");

    click(".o-mail-message-notification").then(() => {});
    await openFormatErrorActionDef;
    assert.verifySteps(["do_action"]);
});

QUnit.test("Missing Required Fields", async function (assert) {
    const openRequiredFieldsActionDef = makeDeferred();
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv["res.partner"].create({});
    const mailMessageId1 = pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "snailmail",
        res_id: resPartnerId1,
        model: "res.partner",
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
    await openFormView("res.partner", resPartnerId1);
    patchWithCleanup(env.services.action, {
        doAction(action, options) {
            assert.step("do_action");
            assert.strictEqual(action, "snailmail.snailmail_letter_missing_required_fields_action");
            assert.strictEqual(options.additionalContext.default_letter_id, snailMailLetterId1);
            openRequiredFieldsActionDef.resolve();
        },
    });

    assert.containsOnce(target, ".o-mail-message");
    assert.containsOnce(target, ".o-mail-message-notification");
    assert.containsOnce(target, ".o-mail-message-notification i");
    assert.hasClass($(target).find(".o-mail-message-notification i"), "fa-paper-plane");

    click(".o-mail-message-notification").then(() => {});
    await openRequiredFieldsActionDef;
    assert.verifySteps(["do_action"]);
});
