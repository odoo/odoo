/** @odoo-module **/

import { click, start, startServer } from "@mail/../tests/helpers/test_utils";
import { getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";

let target;

QUnit.module("notification", {
    async beforeEach() {
        target = getFixture();
    },
});

QUnit.test("basic layout", async function (assert) {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({});
    const messageId = pyEnv["mail.message"].create({
        message_type: "email",
        model: "mail.channel",
        res_id: channelId,
        res_model_name: "Channel",
    });
    pyEnv["mail.notification"].create([
        {
            mail_message_id: messageId,
            notification_status: "exception",
            notification_type: "email",
        },
        {
            mail_message_id: messageId,
            notification_status: "exception",
            notification_type: "email",
        },
    ]);
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsOnce(target, ".o-mail-notification-item-name:contains(Channel)");
    assert.containsOnce(target, ".o-mail-notification-item-counter:contains(2)");
    assert.containsOnce(
        $(target)
            .find(".o-mail-notification-item-name:contains(Channel)")
            .closest(".o-mail-notification-item"),
        ".o-mail-notification-item-date:contains(now)"
    );
    assert.containsOnce(
        target,
        ".o-mail-notification-item-inlineText:contains(An error occurred when sending an email)"
    );
});

QUnit.test("mark as read", async function (assert) {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({});
    const messageId = pyEnv["mail.message"].create({
        message_type: "email",
        model: "mail.channel",
        res_id: channelId,
        res_model_name: "Channel",
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "exception",
        notification_type: "email",
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsOnce(
        $(target)
            .find(".o-mail-notification-item-name:contains(Channel)")
            .closest(".o-mail-notification-item"),
        ".o-mail-notification-item-markAsRead"
    );

    await click(
        $(target)
            .find(".o-mail-notification-item-name:contains(Channel)")
            .closest(".o-mail-notification-item")
            .find(".o-mail-notification-item-markAsRead")
    );
    assert.containsNone(
        $(target)
            .find(".o-mail-notification-item-name:contains(Channel)")
            .closest(".o-mail-notification-item")
    );
});

QUnit.test("open non-channel failure", async function (assert) {
    const pyEnv = await startServer();
    const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
        {
            message_type: "email",
            model: "res.partner",
            res_id: 31,
            res_model_name: "Partner",
        },
        {
            message_type: "email",
            model: "res.partner",
            res_id: 32,
            res_model_name: "Partner",
        },
    ]);
    pyEnv["mail.notification"].create([
        {
            mail_message_id: messageId_1,
            notification_status: "exception",
            notification_type: "email",
        },
        {
            mail_message_id: messageId_2,
            notification_status: "bounce",
            notification_type: "email",
        },
    ]);

    const { env } = await start();
    patchWithCleanup(env.services.action, {
        doAction(action) {
            assert.step("do_action");
            assert.strictEqual(action.name, "Mail Failures");
            assert.strictEqual(action.type, "ir.actions.act_window");
            assert.strictEqual(action.view_mode, "kanban,list,form");
            assert.strictEqual(
                JSON.stringify(action.views),
                JSON.stringify([
                    [false, "kanban"],
                    [false, "list"],
                    [false, "form"],
                ])
            );
            assert.strictEqual(action.target, "current");
            assert.strictEqual(action.res_model, "res.partner");
            assert.strictEqual(
                JSON.stringify(action.domain),
                JSON.stringify([["message_has_error", "=", true]])
            );
        },
    });
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-notification-item");
    assert.verifySteps(["do_action"]);
});

QUnit.test("different mail.channel are not grouped", async function (assert) {
    const pyEnv = await startServer();
    const [channelId_1, channelId_2] = pyEnv["mail.channel"].create([
        { name: "mailChannel1" },
        { name: "mailChannel2" },
    ]);
    const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
        {
            message_type: "email",
            model: "mail.channel",
            res_id: channelId_1,
            res_model_name: "Channel",
        },
        {
            message_type: "email",
            model: "mail.channel",
            res_id: channelId_2,
            res_model_name: "Channel",
        },
    ]);
    pyEnv["mail.notification"].create([
        {
            mail_message_id: messageId_1,
            notification_status: "exception",
            notification_type: "email",
        },
        {
            mail_message_id: messageId_1,
            notification_status: "exception",
            notification_type: "email",
        },
        {
            mail_message_id: messageId_2,
            notification_status: "bounce",
            notification_type: "email",
        },
        {
            mail_message_id: messageId_2,
            notification_status: "bounce",
            notification_type: "email",
        },
    ]);
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsN(
        target,
        ".o-mail-notification-item:contains(An error occurred when sending an email)",
        2
    );
});

QUnit.test("multiple grouped notifications by model", async function (assert) {
    const pyEnv = await startServer();
    const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
        {
            message_type: "email",
            model: "res.partner",
            res_id: 31,
            res_model_name: "Partner",
        },
        {
            message_type: "email",
            model: "res.company",
            res_id: 32,
            res_model_name: "Company",
        },
    ]);
    pyEnv["mail.notification"].create([
        {
            mail_message_id: messageId_1,
            notification_status: "exception",
            notification_type: "email",
        },
        {
            mail_message_id: messageId_1,
            notification_status: "exception",
            notification_type: "email",
        },
        {
            mail_message_id: messageId_2,
            notification_status: "bounce",
            notification_type: "email",
        },
        {
            mail_message_id: messageId_2,
            notification_status: "bounce",
            notification_type: "email",
        },
    ]);
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsN(target, ".o-mail-notification-item", 2);
    assert.containsN(target, ".o-mail-notification-item-counter:contains(2)", 2);
});

QUnit.test("non-failure notifications are ignored", async function (assert) {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const messageId = pyEnv["mail.message"].create({
        message_type: "email",
        model: "res.partner",
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "ready",
        notification_type: "email",
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsNone(target, ".o-mail-notification-item");
});
