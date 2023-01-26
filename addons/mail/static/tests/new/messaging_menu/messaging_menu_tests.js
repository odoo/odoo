/** @odoo-module **/

import { click, start, startServer } from "@mail/../tests/helpers/test_utils";
import { makeFakeNotificationService } from "@web/../tests/helpers/mock_services";
import { getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { patchBrowserNotification } from "@mail/../tests/helpers/patch_notifications";
import { patchUiSize, SIZES } from "@mail/../tests/helpers/patch_ui_size";

let target;

QUnit.module("messaging menu", {
    async beforeEach() {
        target = getFixture();
    },
});

QUnit.test("should have messaging menu button in systray", async (assert) => {
    await start();
    assert.containsOnce(target, ".o_menu_systray i[aria-label='Messages']");
    assert.containsNone(target, ".o-mail-messaging-menu", "messaging menu closed by default");
    assert.hasClass(
        target.querySelector(".o_menu_systray i[aria-label='Messages']"),
        "fa-comments"
    );
});

QUnit.test("messaging menu should have topbar buttons", async function (assert) {
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsOnce(target, ".o-mail-messaging-menu");
    assert.containsN(target, ".o-mail-messaging-menu-topbar button", 4);
    assert.containsOnce(target, "button:contains(All)");
    assert.containsOnce(target, "button:contains(Chat)");
    assert.containsOnce(target, "button:contains(Channels)");
    assert.containsOnce(target, "button:contains(New Message)");
    assert.hasClass($(target).find("button:contains(All)"), "fw-bolder");
    assert.doesNotHaveClass($(target).find("button:contains(Chat)"), "fw-bolder");
    assert.doesNotHaveClass($(target).find("button:contains(Channels)"), "fw-bolder");
});

QUnit.test("counter is taking into account failure notification", async function (assert) {
    patchBrowserNotification("denied");
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({});
    const messageId = pyEnv["mail.message"].create({
        model: "mail.channel",
        res_id: channelId,
    });
    const [memberId] = pyEnv["mail.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", pyEnv.currentPartnerId],
    ]);
    pyEnv["mail.channel.member"].write([memberId], {
        seen_message_id: messageId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "exception",
        notification_type: "email",
    });
    await start();
    assert.containsOnce(target, ".o-mail-messaging-menu-counter");
    assert.strictEqual($(target).find(".o-mail-messaging-menu-counter.badge").text(), "1");
});

QUnit.test("rendering with OdooBot has a request (default)", async function (assert) {
    patchBrowserNotification("default");
    await start();
    assert.containsOnce(target, ".o-mail-messaging-menu-counter");
    assert.strictEqual($(target).find(".o-mail-messaging-menu-counter").text(), "1");
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsOnce(target, ".o-mail-notification-item");
    assert.strictEqual(
        target.querySelector(".o-mail-notification-item-name").textContent.trim(),
        "OdooBot has a request"
    );
});

QUnit.test("rendering without OdooBot has a request (denied)", async function (assert) {
    patchBrowserNotification("denied");
    await start();
    assert.strictEqual($(target).find(".o-mail-messaging-menu-counter").text(), "0");
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsNone(target, ".o-mail-notification-item");
});

QUnit.test("rendering without OdooBot has a request (accepted)", async function (assert) {
    patchBrowserNotification("granted");
    await start();
    assert.strictEqual($(target).find(".o-mail-messaging-menu-counter").text(), "0");
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsNone(target, ".o-mail-notification-item");
});

QUnit.test("respond to notification prompt (denied)", async function (assert) {
    patchBrowserNotification("default", "denied");
    await start({
        services: {
            notification: makeFakeNotificationService(() => {
                assert.step("confirmation_denied_toast");
            }),
        },
    });
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-notification-item");
    assert.verifySteps(["confirmation_denied_toast"]);
    assert.strictEqual($(target).find(".o-mail-messaging-menu-counter").text(), "0");
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsNone(target, ".o-mail-notification-item");
});

QUnit.test("Is closed after clicking on new message", async function (assert) {
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-messaging-menu-new-message");
    assert.containsNone(target, ".o-mail-messaging-menu");
});

QUnit.test("no 'New Message' button when discuss is open", async function (assert) {
    const { openDiscuss, openView } = await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsOnce(target, "button:contains(New Message)");

    await openDiscuss();
    assert.containsNone(target, "button:contains(New Message)");

    await openView({
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    assert.containsOnce(target, "button:contains(New Message)");

    await openDiscuss();
    assert.containsNone(target, "button:contains(New Message)");
});

QUnit.test("grouped notifications by document", async function (assert) {
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
            res_id: 31,
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
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsOnce(target, ".o-mail-notification-item");
    assert.containsOnce(target, ".o-mail-notification-item:contains(Partner (2))");
    assert.containsNone(target, ".o-mail-chat-window");

    await click(".o-mail-notification-item");
    assert.containsOnce(target, ".o-mail-chat-window");
});

QUnit.test("grouped notifications by document model", async function (assert) {
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
    assert.containsOnce(target, ".o-mail-notification-item:contains(Partner (2))");

    document.querySelector(".o-mail-notification-item").click();
    assert.verifySteps(["do_action"]);
});

QUnit.test(
    "multiple grouped notifications by document model, sorted by the most recent message of each group",
    async function (assert) {
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
        const items = target.querySelectorAll(".o-mail-notification-item");
        assert.ok(items[0].textContent.includes("Company"));
        assert.ok(items[1].textContent.includes("Partner"));
    }
);

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

QUnit.test("mark unread channel as read", async function (assert) {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const channelId = pyEnv["mail.channel"].create({
        channel_member_ids: [
            [0, 0, { message_unread_counter: 1, partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId }],
        ],
    });
    const [messagId_1] = pyEnv["mail.message"].create([
        { author_id: partnerId, model: "mail.channel", res_id: channelId },
        { author_id: partnerId, model: "mail.channel", res_id: channelId },
    ]);
    const [currentMemberId] = pyEnv["mail.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", pyEnv.currentPartnerId],
    ]);
    pyEnv["mail.channel.member"].write([currentMemberId], { seen_message_id: messagId_1 });
    await start({
        async mockRPC(route, args) {
            if (route.includes("set_last_seen_message")) {
                assert.step("set_last_seen_message");
            }
        },
    });
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsOnce(target, ".o-mail-notification-item i[title='Mark As Read']");

    await click(".o-mail-notification-item i[title='Mark As Read']");
    assert.verifySteps(["set_last_seen_message"]);
    assert.hasClass(target.querySelector(".o-mail-notification-item"), "o-muted");
    assert.containsNone(target, ".o-mail-notification-item i[title='Mark As Read']");
    assert.containsNone(target, ".o-mail-chat-window");
});

QUnit.test("mark failure as read", async function (assert) {
    const pyEnv = await startServer();
    const messageId = pyEnv["mail.message"].create({
        message_type: "email",
        res_model_name: "Channel",
    });
    pyEnv["mail.channel"].create({
        message_ids: [messageId],
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId, seen_message_id: messageId }],
        ],
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "exception",
        notification_type: "email",
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    assert.containsOnce(target, ".o-mail-notification-item:contains(Channel)");
    assert.containsOnce(
        target,
        ".o-mail-notification-item:contains(An error occurred when sending an email)"
    );
    assert.containsOnce(
        target,
        ".o-mail-notification-item:contains(Channel) i[title='Mark As Read']"
    );

    await click(".o-mail-notification-item i[title='Mark As Read']");
    assert.containsNone(target, ".o-mail-notification-item:contains(Channel)");
    assert.containsNone(
        target,
        ".o-mail-notification-item:contains(An error occurred when sending an email)"
    );
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
    assert.containsN(target, ".o-mail-notification-item", 4);

    const group_1 = $(".o-mail-notification-item:contains(Channel (2)):first");
    await click(group_1);
    assert.containsOnce(target, ".o-mail-chat-window");
});

QUnit.test("mobile: active icon is highlighted", async function (assert) {
    patchUiSize({ size: SIZES.SM });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-messaging-menu-tab:contains(Chat)");
    assert.hasClass($(target).find(".o-mail-messaging-menu-tab:contains(Chat)"), "fw-bolder");
});

QUnit.test("open chat window from preview", async function (assert) {
    const pyEnv = await startServer();
    pyEnv["mail.channel"].create({ name: "test" });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-notification-item");
    assert.containsOnce(target, ".o-mail-chat-window");
});
