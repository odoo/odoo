/** @odoo-module **/

import { TEST_USER_IDS } from "@bus/../tests/helpers/test_constants";
import { patchUiSize } from "@mail/../tests/helpers/patch_ui_size";
import { Command } from "@mail/../tests/helpers/command";

import {
    isScrolledToBottom,
    afterNextRender,
    click,
    createFile,
    insertText,
    start,
    startServer,
    waitUntil,
} from "@mail/../tests/helpers/test_utils";
import { editInput, nextTick, triggerEvent, triggerHotkey } from "@web/../tests/helpers/utils";
import { makeFakeNotificationService } from "@web/../tests/helpers/mock_services";
import { makeFakePresenceService } from "@bus/../tests/helpers/mock_services";

QUnit.module("discuss");

QUnit.test("sanity check", async (assert) => {
    const { openDiscuss } = await start({
        mockRPC(route, args, originRPC) {
            if (route.startsWith("/mail")) {
                assert.step(route);
            }
            return originRPC(route, args);
        },
    });
    await openDiscuss();
    assert.containsOnce($, ".o-mail-DiscussSidebar");
    assert.containsOnce($, "h4:contains(Congratulations, your inbox is empty)");
    assert.verifySteps([
        "/mail/init_messaging",
        "/mail/load_message_failures",
        "/mail/inbox/messages",
    ]);
});

QUnit.test("can change the thread name of #general", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    const { openDiscuss } = await start({
        mockRPC(route, params) {
            if (route === "/web/dataset/call_kw/discuss.channel/channel_rename") {
                assert.step(route);
            }
        },
    });
    await openDiscuss(channelId);
    assert.containsOnce($, "input.o-mail-Discuss-threadName");
    const $name = $("input.o-mail-Discuss-threadName");

    click($name).catch(() => {});
    assert.strictEqual($name.val(), "general");
    await editInput(document.body, "input.o-mail-Discuss-threadName", "special");
    await triggerEvent(document.body, "input.o-mail-Discuss-threadName", "keydown", {
        key: "Enter",
    });
    assert.strictEqual($name.val(), "special");
    assert.verifySteps(["/web/dataset/call_kw/discuss.channel/channel_rename"]);
});

QUnit.test("can change the thread description of #general", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
        description: "General announcements...",
    });
    const { openDiscuss } = await start({
        mockRPC(route, params) {
            if (route === "/web/dataset/call_kw/discuss.channel/channel_change_description") {
                assert.step(route);
            }
        },
    });
    await openDiscuss(channelId);
    assert.containsOnce($, "input.o-mail-Discuss-threadDescription");
    const $description = $("input.o-mail-Discuss-threadDescription");

    click($description).then(() => {});
    assert.strictEqual($description.val(), "General announcements...");
    await editInput(
        document.body,
        "input.o-mail-Discuss-threadDescription",
        "I want a burger today!"
    );
    await triggerEvent(document.body, "input.o-mail-Discuss-threadDescription", "keydown", {
        key: "Enter",
    });
    assert.strictEqual($description.val(), "I want a burger today!");
    assert.verifySteps(["/web/dataset/call_kw/discuss.channel/channel_change_description"]);
});

QUnit.test("can create a new channel [REQUIRE FOCUS]", async (assert) => {
    await startServer();
    const { openDiscuss } = await start({
        mockRPC(route, params) {
            if (
                route.startsWith("/mail") ||
                route.startsWith("/discuss") ||
                [
                    "/web/dataset/call_kw/discuss.channel/search_read",
                    "/web/dataset/call_kw/discuss.channel/channel_create",
                ].includes(route)
            ) {
                assert.step(route);
            }
        },
    });
    await openDiscuss();
    assert.containsNone($, ".o-mail-DiscussCategoryItem");

    await click(".o-mail-DiscussSidebar i[title='Add or join a channel']");
    await afterNextRender(() => editInput(document.body, ".o-mail-ChannelSelector input", "abc"));
    await click(".o-mail-ChannelSelector-suggestion");
    assert.containsOnce($, ".o-mail-DiscussCategoryItem");
    assert.containsNone($, ".o-mail-Discuss-content .o-mail-Message");
    assert.verifySteps([
        "/mail/init_messaging",
        "/mail/load_message_failures",
        "/mail/inbox/messages",
        "/web/dataset/call_kw/discuss.channel/search_read",
        "/web/dataset/call_kw/discuss.channel/channel_create",
        "/discuss/channel/messages",
    ]);
});

QUnit.test(
    "do not close channel selector when creating chat conversation after selection",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Mario" });
        pyEnv["res.users"].create({ partner_id: partnerId });
        const { openDiscuss } = await start();
        await openDiscuss();
        assert.containsNone($, ".o-mail-DiscussCategoryItem");

        await click("i[title='Start a conversation']");
        await afterNextRender(() =>
            editInput(document.body, ".o-mail-ChannelSelector input", "mario")
        );
        await click(".o-mail-ChannelSelector-suggestion");
        assert.containsOnce($, ".o-mail-ChannelSelector span[title='Mario']");
        assert.containsNone($, ".o-mail-DiscussCategoryItem");

        await triggerEvent(document.body, ".o-mail-ChannelSelector input", "keydown", {
            key: "Backspace",
        });
        assert.containsNone($, ".o-mail-ChannelSelector span[title='Mario']");

        await afterNextRender(() =>
            editInput(document.body, ".o-mail-ChannelSelector input", "mario")
        );
        await triggerEvent(document.body, ".o-mail-ChannelSelector input", "keydown", {
            key: "Enter",
        });
        assert.containsOnce($, ".o-mail-ChannelSelector span[title='Mario']");
        assert.containsNone($, ".o-mail-DiscussCategoryItem");
    }
);

QUnit.test("can join a chat conversation", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Mario" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const { openDiscuss } = await start({
        mockRPC(route, params) {
            if (
                route.startsWith("/mail") ||
                route.startsWith("/discuss") ||
                ["/web/dataset/call_kw/discuss.channel/channel_get"].includes(route)
            ) {
                assert.step(route);
            }
            if (route === "/web/dataset/call_kw/discuss.channel/channel_get") {
                assert.equal(params.kwargs.partners_to[0], partnerId);
            }
        },
    });
    await openDiscuss();
    assert.containsNone($, ".o-mail-DiscussCategoryItem");

    await click(".o-mail-DiscussSidebar i[title='Start a conversation']");
    await afterNextRender(() => editInput(document.body, ".o-mail-ChannelSelector input", "mario"));
    await click(".o-mail-ChannelSelector-suggestion");
    await triggerEvent(document.body, ".o-mail-ChannelSelector input", "keydown", {
        key: "Enter",
    });
    assert.containsOnce($, ".o-mail-DiscussCategoryItem");
    assert.containsNone($, ".o-mail-Message");
    assert.verifySteps([
        "/mail/init_messaging",
        "/mail/load_message_failures",
        "/mail/inbox/messages",
        "/web/dataset/call_kw/discuss.channel/channel_get",
        "/discuss/channel/messages",
    ]);
});

QUnit.test("can create a group chat conversation", async (assert) => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { name: "Mario" },
        { name: "Luigi" },
    ]);
    pyEnv["res.users"].create([{ partner_id: partnerId_1 }, { partner_id: partnerId_2 }]);
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsNone($, ".o-mail-DiscussCategoryItem");
    await click(".o-mail-DiscussSidebar i[title='Start a conversation']");
    await insertText(".o-mail-ChannelSelector input", "Mario");
    await click(".o-mail-ChannelSelector-suggestion");
    await insertText(".o-mail-ChannelSelector input", "Luigi");
    await click(".o-mail-ChannelSelector-suggestion");
    await triggerEvent(document.body, ".o-mail-ChannelSelector input", "keydown", {
        key: "Enter",
    });
    assert.containsN($, ".o-mail-DiscussCategoryItem", 1);
    assert.containsNone($, ".o-mail-Message");
});

QUnit.test("chat search should display no result when no matches found", async (assert) => {
    const { openDiscuss } = await start();
    await openDiscuss();
    await click(".o-mail-DiscussSidebar i[title='Start a conversation']");
    await insertText(".o-mail-ChannelSelector", "Rainbow Panda");
    assert.containsOnce($, ".o-mail-ChannelSelector-suggestion:contains(No results found)");
});

QUnit.test(
    "chat search should not be visible when clicking outside of the field",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Panda" });
        pyEnv["res.users"].create({ partner_id: partnerId });
        const { openDiscuss } = await start();
        await openDiscuss();
        assert.containsNone($, ".o-mail-DiscussCategoryItem");
        await click(".o-mail-DiscussSidebar i[title='Start a conversation']");
        await insertText(".o-mail-ChannelSelector", "Panda");
        assert.containsOnce($, ".o-mail-ChannelSelector-suggestion");
        await click(".o-mail-DiscussSidebar");
        assert.containsNone($, ".o-mail-ChannelSelector-suggestion");
    }
);

QUnit.test("Message following a notification should not be squashed", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: '<div class="o_mail_notification">created <a href="#" class="o_channel_redirect">#general</a></div>',
        model: "discuss.channel",
        res_id: channelId,
        message_type: "notification",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await editInput(document.body, ".o-mail-Composer-input", "Hello world!");
    await click(".o-mail-Composer button:contains(Send)");
    assert.containsOnce($, ".o-mail-Message-sidebar .o-mail-Message-avatarContainer");
});

QUnit.test("Posting message should transform links.", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "test https://www.odoo.com/");
    await click(".o-mail-Composer-send");
    assert.containsOnce($, "a[href='https://www.odoo.com/']");
});

QUnit.test("Posting message should transform relevant data to emoji.", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "test :P :laughing:");
    await click(".o-mail-Composer-send");
    assert.containsOnce($, ".o-mail-Message-body:contains(test 😛 😆)");
});

QUnit.test(
    "posting a message immediately after another one is displayed in 'simple' mode (squashed)",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({
            name: "general",
            channel_type: "channel",
        });
        let flag = false;
        const { openDiscuss } = await start({
            async mockRPC(route, params) {
                if (flag && route === "/mail/message/post") {
                    await new Promise(() => {});
                }
            },
        });

        await openDiscuss(channelId);
        // write 1 message
        await editInput(document.body, ".o-mail-Composer-input", "abc");
        await click(".o-mail-Composer button:contains(Send)");

        // write another message, but /mail/message/post is delayed by promise
        flag = true;
        await editInput(document.body, ".o-mail-Composer-input", "def");
        await click(".o-mail-Composer button:contains(Send)");
        assert.containsN($, ".o-mail-Message", 2);
        assert.containsN($, ".o-mail-Message-header", 1); // just 1, because 2nd message is squashed
    }
);

QUnit.test("Click on avatar opens its partner chat window", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "testPartner" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    pyEnv["mail.message"].create({
        author_id: partnerId,
        body: "Test",
        attachment_ids: [],
        model: "res.partner",
        res_id: partnerId,
    });
    const { openFormView } = await start();
    await openFormView("res.partner", partnerId);
    assert.containsOnce($, ".o-mail-Message-sidebar .o-mail-Message-avatarContainer img");
    await click(".o-mail-Message-sidebar .o-mail-Message-avatarContainer img");
    assert.containsOnce($, ".o-mail-ChatWindow-name");
    assert.ok($(".o-mail-ChatWindow-name").text().includes("testPartner"));
});

QUnit.test("Can use channel command /who", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "my-channel",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "/who");
    await click(".o-mail-Composer button:contains(Send)");
    assert.strictEqual($(".o_mail_notification").text(), "You are alone in this channel.");
});

QUnit.test("sidebar: chat im_status rendering", async (assert) => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2, partnerId_3] = pyEnv["res.partner"].create([
        { im_status: "offline", name: "Partner1" },
        { im_status: "online", name: "Partner2" },
        { im_status: "away", name: "Partner3" },
    ]);
    pyEnv["discuss.channel"].create([
        {
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId }),
                Command.create({ partner_id: partnerId_1 }),
            ],
            channel_type: "chat",
        },
        {
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId }),
                Command.create({ partner_id: partnerId_2 }),
            ],
            channel_type: "chat",
        },
        {
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId }),
                Command.create({ partner_id: partnerId_3 }),
            ],
            channel_type: "chat",
        },
    ]);
    const { openDiscuss } = await start({ hasTimeControl: true });
    await openDiscuss();
    assert.containsN($, ".o-mail-DiscussCategoryItem-threadIcon", 3);
    const chat1 = $(".o-mail-DiscussCategoryItem")[0];
    const chat2 = $(".o-mail-DiscussCategoryItem")[1];
    const chat3 = $(".o-mail-DiscussCategoryItem")[2];
    assert.strictEqual(chat1.textContent, "Partner1");
    assert.strictEqual(chat2.textContent, "Partner2");
    assert.strictEqual(chat3.textContent, "Partner3");
    assert.containsOnce(chat1, ".o-mail-ThreadIcon div[title='Offline']");
    assert.containsOnce(chat2, ".fa-circle.text-success");
    assert.containsOnce(chat3, ".o-mail-ThreadIcon div[title='Away']");
});

QUnit.test("No load more when fetch below fetch limit of 30", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["res.partner"].create({});
    for (let i = 28; i >= 0; i--) {
        pyEnv["mail.message"].create({
            author_id: partnerId,
            body: "not empty",
            date: "2019-04-20 10:00:00",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === "/discuss/channel/messages") {
                assert.strictEqual(args.limit, 30);
            }
        },
    });
    await openDiscuss(channelId);
    assert.containsN($, ".o-mail-Message", 29);
    assert.containsNone($, "button:contains(Load more)");
});

QUnit.test("show date separator above mesages of similar date", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["res.partner"].create({});
    for (let i = 28; i >= 0; i--) {
        pyEnv["mail.message"].create({
            author_id: partnerId,
            body: "not empty",
            date: "2019-04-20 10:00:00",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.ok(
        $("hr + span:contains(April 20, 2019) + hr").offset().top <
            $(".o-mail-Message").offset().top,
        "should have a single date separator above all the messages" // to check: may be client timezone dependent
    );
});

QUnit.test("sidebar: chat custom name", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Marc Demo" });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ custom_channel_name: "Marc", partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.strictEqual($(".o-mail-DiscussCategoryItem span").text(), "Marc");
});

QUnit.test("reply to message from inbox (message linked to document)", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Refactoring" });
    const messageId = pyEnv["mail.message"].create({
        body: "<p>Test</p>",
        date: "2019-04-20 11:00:00",
        message_type: "comment",
        needaction: true,
        model: "res.partner",
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_type: "inbox",
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === "/mail/message/post") {
                assert.step("message_post");
                assert.strictEqual(args.thread_model, "res.partner");
                assert.strictEqual(args.thread_id, partnerId);
                assert.strictEqual(args.post_data.body, "Test");
                assert.strictEqual(args.post_data.message_type, "comment");
            }
        },
        services: {
            notification: makeFakeNotificationService((notification) => {
                assert.ok(true);
                assert.strictEqual(notification, 'Message posted on "Refactoring"');
            }),
        },
    });
    await openDiscuss();
    assert.containsOnce($, ".o-mail-Message");
    assert.containsOnce($, ".o-mail-Message-header:contains(on Refactoring)");

    await click("[title='Reply']");
    assert.hasClass($(".o-mail-Message"), "o-selected");
    assert.containsOnce($, ".o-mail-Composer");
    assert.containsOnce($, ".o-mail-Composer-coreHeader:contains(on: Refactoring)");
    assert.strictEqual(document.activeElement, $(".o-mail-Composer-input")[0]);

    await insertText(".o-mail-Composer-input", "Test");
    await click(".o-mail-Composer-send");
    assert.verifySteps(["message_post"]);
    assert.containsNone($, ".o-mail-Composer");
    assert.containsOnce($, ".o-mail-Message");
    assert.containsOnce($, ".o-mail-Message:contains(Test)");
    assert.doesNotHaveClass($(".o-mail-Message"), "o-selected");
});

QUnit.test("Can reply to starred message", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "RandomName" });
    pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        starred_partner_ids: [pyEnv.currentPartnerId],
        res_id: channelId,
    });
    const { openDiscuss } = await start({
        services: {
            notification: makeFakeNotificationService((message) => assert.step(message)),
        },
    });
    await openDiscuss("mail.box_starred");
    await click("[title='Reply']");
    assert.containsOnce($, ".o-mail-Composer-coreHeader:contains('RandomName')");
    await insertText(".o-mail-Composer-input", "abc");
    await click(".o-mail-Composer-send");
    assert.verifySteps(['Message posted on "RandomName"']);
    assert.containsOnce($, ".o-mail-Message");
});

QUnit.test("Can reply to history message", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "RandomName" });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        history_partner_ids: [pyEnv.currentPartnerId],
        res_id: channelId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_type: "inbox",
        res_partner_id: pyEnv.currentPartnerId,
        is_read: true,
    });
    const { openDiscuss } = await start({
        services: {
            notification: makeFakeNotificationService((message) => assert.step(message)),
        },
    });
    await openDiscuss("mail.box_history");
    await click("[title='Reply']");
    assert.containsOnce($, ".o-mail-Composer-coreHeader:contains('RandomName')");
    await insertText(".o-mail-Composer-input", "abc");
    await click(".o-mail-Composer-send");
    assert.verifySteps(['Message posted on "RandomName"']);
    assert.containsOnce($, ".o-mail-Message");
});

QUnit.test("receive new needaction messages", async (assert) => {
    const { openDiscuss, pyEnv } = await start();
    await openDiscuss();
    assert.containsOnce($, "button:contains(Inbox)");
    assert.hasClass($("button:contains(Inbox)"), "o-active");
    assert.containsNone($, "button:contains(Inbox) .badge");
    assert.containsNone($, ".o-mail-Thread .o-mail-Message");

    // simulate receiving a new needaction message
    await afterNextRender(() => {
        pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "mail.message/inbox", {
            body: "not empty 1",
            id: 100,
            needaction_partner_ids: [pyEnv.currentPartnerId],
            model: "res.partner",
            res_id: 20,
        });
    });
    assert.containsOnce($, "button:contains(Inbox) .badge");
    assert.containsOnce($, "button:contains(Inbox) .badge:contains(1)");
    assert.containsOnce($, ".o-mail-Message");
    assert.containsOnce($, ".o-mail-Message:contains(not empty 1)");

    // simulate receiving another new needaction message
    await afterNextRender(() => {
        pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "mail.message/inbox", {
            body: "not empty 2",
            id: 101,
            needaction_partner_ids: [pyEnv.currentPartnerId],
            model: "res.partner",
            res_id: 20,
        });
    });
    assert.containsOnce($, "button:contains(Inbox) .badge:contains(2)");
    assert.containsN($, ".o-mail-Message", 2);
    assert.containsOnce($, ".o-mail-Message:contains(not empty 1)");
    assert.containsOnce($, ".o-mail-Message:contains(not empty 2)");
});

QUnit.test("basic rendering", async (assert) => {
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, ".o-mail-DiscussSidebar");
    assert.containsOnce($, ".o-mail-Discuss-content");
    assert.containsOnce($, ".o-mail-Discuss-content .o-mail-Thread");
});

QUnit.test("basic rendering: sidebar", async (assert) => {
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, ".o-mail-DiscussSidebar button:contains(Inbox)");
    assert.containsOnce($, ".o-mail-DiscussSidebar button:contains(Starred)");
    assert.containsOnce($, ".o-mail-DiscussSidebar button:contains(History)");
    assert.containsN($, ".o-mail-DiscussCategory", 2);
    assert.containsOnce($, ".o-mail-DiscussCategory-channel");
    assert.containsOnce($, ".o-mail-DiscussCategory-chat");
    assert.strictEqual($(".o-mail-DiscussCategory-channel").text(), "Channels");
    assert.strictEqual($(".o-mail-DiscussCategory-chat").text(), "Direct messages");
});

QUnit.test("sidebar: Inbox should have icon", async (assert) => {
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, "button:contains(Inbox)");
    assert.containsOnce($("button:contains(Inbox)"), ".fa-inbox");
});

QUnit.test("sidebar: default active inbox", async (assert) => {
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, "button:contains(Inbox)");
    assert.hasClass($("button:contains(Inbox)"), "o-active");
});

QUnit.test("sidebar: change active", async (assert) => {
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, "button:contains(Inbox)");
    assert.containsOnce($, "button:contains(Starred)");
    assert.hasClass($("button:contains(Inbox)"), "o-active");
    assert.doesNotHaveClass($("button:contains(Starred)"), "o-active");
    await click("button:contains(Starred)");
    assert.doesNotHaveClass($("button:contains(Inbox)"), "o-active");
    assert.hasClass($("button:contains(Starred)"), "o-active");
});

QUnit.test("sidebar: add channel", async (assert) => {
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, ".o-mail-DiscussCategory-channel .o-mail-DiscussCategory-add");
    assert.hasAttrValue(
        $(".o-mail-DiscussCategory-channel .o-mail-DiscussCategory-add")[0],
        "title",
        "Add or join a channel"
    );
    await click(".o-mail-DiscussCategory-channel .o-mail-DiscussCategory-add");
    assert.containsOnce($, ".o-mail-ChannelSelector");
    assert.containsOnce($, ".o-mail-ChannelSelector input[placeholder='Add or join a channel']");
});

QUnit.test("sidebar: basic channel rendering", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, ".o-mail-DiscussCategoryItem");
    assert.strictEqual($(".o-mail-DiscussCategoryItem").text(), "General");
    assert.containsOnce($(".o-mail-DiscussCategoryItem"), "img[data-alt='Thread Image']");
    assert.containsOnce($(".o-mail-DiscussCategoryItem"), ".o-mail-DiscussCategoryItem-commands");
    assert.hasClass(
        $(".o-mail-DiscussCategoryItem .o-mail-DiscussCategoryItem-commands"),
        "d-none"
    );
    assert.containsOnce(
        $(".o-mail-DiscussCategoryItem .o-mail-DiscussCategoryItem-commands"),
        "i[title='Channel settings']"
    );
    assert.containsOnce(
        $(".o-mail-DiscussCategoryItem .o-mail-DiscussCategoryItem-commands"),
        "div[title='Leave this channel']"
    );
});

QUnit.test("channel become active", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, ".o-mail-DiscussCategoryItem");
    assert.containsNone($, ".o-mail-DiscussCategoryItem.o-active");
    await click(".o-mail-DiscussCategoryItem");
    assert.containsOnce($, ".o-mail-DiscussCategoryItem.o-active");
});

QUnit.test("channel become active - show composer in discuss content", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss();
    await click(".o-mail-DiscussCategoryItem");
    assert.containsOnce($, ".o-mail-Thread");
    assert.containsOnce($, ".o-mail-Composer");
});

QUnit.test("sidebar: channel rendering with needaction counter", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_type: "inbox",
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, ".o-mail-DiscussCategoryItem:contains(general)");
    assert.containsOnce($, ".o-mail-DiscussCategoryItem:contains(general) .badge:contains(1)");
});

QUnit.test("sidebar: chat rendering with unread counter", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ message_unread_counter: 100, partner_id: pyEnv.currentPartnerId }),
        ],
        channel_type: "chat",
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, ".o-mail-DiscussCategoryItem .badge:contains(100)");
    assert.containsNone(
        $,
        ".o-mail-DiscussCategoryItem .o-mail-DiscussCategoryItem-commands:contains(Unpin Conversation)"
    );
});

QUnit.test("initially load messages from inbox", async (assert) => {
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === "/mail/inbox/messages") {
                assert.step("/discuss/channel/messages");
                assert.strictEqual(args.limit, 30);
            }
        },
    });
    await openDiscuss();
    assert.verifySteps(["/discuss/channel/messages"]);
});

QUnit.test("default active id on mailbox", async (assert) => {
    const { openDiscuss } = await start();
    await openDiscuss("mail.box_starred");
    assert.hasClass($("button:contains(Starred)"), "o-active");
});

QUnit.test("basic top bar rendering", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.strictEqual($(".o-mail-Discuss-threadName").val(), "Inbox");
    const $markAllRead = $("button:contains(Mark all read)");
    assert.isVisible($markAllRead);
    assert.ok($markAllRead[0].disabled);

    await click("button:contains(Starred)");
    assert.strictEqual($(".o-mail-Discuss-threadName").val(), "Starred");
    const $unstarAll = $("button:contains(Unstar all)");
    assert.isVisible($unstarAll);
    assert.ok($unstarAll[0].disabled);

    await click(".o-mail-DiscussCategoryItem:contains(General)");
    assert.strictEqual($(".o-mail-Discuss-threadName").val(), "General");
    assert.isVisible($(".o-mail-Discuss-header button[title='Add Users']"));
});

QUnit.test("rendering of inbox message", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Refactoring" });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.partner",
        needaction: true,
        needaction_partner_ids: [pyEnv.currentPartnerId],
        res_id: partnerId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, ".o-mail-Message");
    const $message = $(".o-mail-Message");
    assert.containsOnce($message, ".o-mail-Message-header:contains(on Refactoring)");
    assert.containsN($message, ".o-mail-Message-actions i", 4);
    assert.containsOnce($message, "[title='Reply']");
    assert.containsOnce($message, "[title='Mark as Todo']");
    assert.containsOnce($message, "[title='Mark as Read']");
    assert.containsOnce($message, "[title='Expand']");
    await click("[title='Expand']");
    assert.containsN($message, ".o-mail-Message-actions i", 5);
    assert.containsOnce($message, "[title='Reply']");
    assert.containsOnce($message, "[title='Mark as Todo']");
    assert.containsOnce($message, "[title='Mark as Read']");
    assert.containsOnce($message, "[title='Expand']");
    assert.containsOnce($message, "[title='Add a Reaction']");
});

QUnit.test("Unfollow message", async function (assert) {
    assert.expect(12);

    const pyEnv = await startServer();
    const currentPartnerId = pyEnv.currentPartnerId;
    const [threadFollowedId, threadNotFollowedId] = pyEnv["res.partner"].create([
        {
            name: "Thread followed",
        },
        {
            name: "Thread not followed",
        },
    ]);
    pyEnv["mail.followers"].create({
        partner_id: currentPartnerId,
        res_id: threadFollowedId,
        res_model: "res.partner",
    });
    for (const threadId of [threadFollowedId, threadFollowedId, threadNotFollowedId]) {
        const messageId = pyEnv["mail.message"].create({
            body: "not empty",
            model: "res.partner",
            needaction: true,
            needaction_partner_ids: [currentPartnerId],
            res_id: threadId,
        });
        pyEnv["mail.notification"].create({
            mail_message_id: messageId,
            notification_status: "sent",
            notification_type: "inbox",
            res_partner_id: currentPartnerId,
        });
    }
    const { openDiscuss } = await start();
    await openDiscuss();
    // 2 messages about "Thread followed" with unfollow button and 1 message about "Thread not followed" without it
    assert.containsN($, ".o-mail-Message", 3);
    for (const messageN of [0, 1]) {
        const $message = $(`.o-mail-Message:eq(${messageN})`);
        assert.containsOnce($message, ".o-mail-Message-header:contains(on Thread followed)");
        await afterNextRender(() => $message.find("[title='Expand']").click());
        assert.containsOnce($message, "[title='Unfollow']");
    }
    const $messageNotFollowed = $(".o-mail-Message:eq(2)");
    assert.containsOnce(
        $messageNotFollowed,
        ".o-mail-Message-header:contains(on Thread not followed)"
    );
    await afterNextRender(() => $messageNotFollowed.find("[title='Expand']").click());
    assert.containsNone($messageNotFollowed, "[title='Unfollow']");

    const $message0Followed = $(".o-mail-Message:eq(0)");
    await afterNextRender(() => $message0Followed.find("[title='Expand']").click());
    await afterNextRender(() => $message0Followed.find("[title='Unfollow']").click());

    assert.containsN(
        $,
        ".o-mail-Message",
        2,
        "Unfollowing message 0 marks it as read -> Message removed"
    );
    assert.containsOnce($, ".o-mail-Message-header:contains(on Thread followed)");
    assert.containsOnce($, ".o-mail-Message-header:contains(on Thread not followed)");
    for (const messageN of [0, 1]) {
        const $message = $(`.o-mail-Message:eq(${messageN})`);
        await afterNextRender(() => $message.find("[title='Expand']").click());
        assert.containsNone(
            $,
            "button[title='Unfollow']",
            "Unfollowing message 0 -> unfollowing 'Thread followed' -> no more unfollow action on any message"
        );
    }
});

QUnit.test('messages marked as read move to "History" mailbox', async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "other-disco" });
    const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
        {
            body: "not empty",
            model: "discuss.channel",
            needaction: true,
            res_id: channelId,
        },
        {
            body: "not empty",
            model: "discuss.channel",
            needaction: true,
            res_id: channelId,
        },
    ]);
    pyEnv["mail.notification"].create([
        {
            mail_message_id: messageId_1,
            notification_type: "inbox",
            res_partner_id: pyEnv.currentPartnerId,
        },
        {
            mail_message_id: messageId_2,
            notification_type: "inbox",
            res_partner_id: pyEnv.currentPartnerId,
        },
    ]);
    const { openDiscuss } = await start();
    await openDiscuss("mail.box_history");
    assert.hasClass($("button:contains(History)"), "o-active");
    assert.containsOnce($, ".o-mail-Thread:contains(No history messages)");

    await click("button:contains(Inbox)");
    assert.hasClass($("button:contains(Inbox)"), "o-active");
    assert.containsNone($, ".o-mail-Thread:contains(Congratulations, your inbox is empty)");
    assert.containsN($, ".o-mail-Thread .o-mail-Message", 2);

    await click("button:contains(Mark all read)");
    assert.hasClass($("button:contains(Inbox)"), "o-active");
    assert.containsOnce($, ".o-mail-Thread:contains(Congratulations, your inbox is empty)");

    await click("button:contains(History)");
    assert.hasClass($("button:contains(History)"), "o-active");
    assert.containsNone($, ".o-mail-Thread:contains(No history messages)");
    assert.containsN($, ".o-mail-Thread .o-mail-Message", 2);
});

QUnit.test(
    'mark a single message as read should only move this message to "History" mailbox',
    async (assert) => {
        const pyEnv = await startServer();
        const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
            {
                body: "not empty 1",
                needaction: true,
                needaction_partner_ids: [pyEnv.currentPartnerId],
            },
            {
                body: "not empty 2",
                needaction: true,
                needaction_partner_ids: [pyEnv.currentPartnerId],
            },
        ]);
        pyEnv["mail.notification"].create([
            {
                mail_message_id: messageId_1,
                notification_type: "inbox",
                res_partner_id: pyEnv.currentPartnerId,
            },
            {
                mail_message_id: messageId_2,
                notification_type: "inbox",
                res_partner_id: pyEnv.currentPartnerId,
            },
        ]);
        const { openDiscuss } = await start();
        await openDiscuss("mail.box_history");
        assert.hasClass($("button:contains(History)"), "o-active");
        assert.containsOnce($, ".o-mail-Thread:contains(No history messages)");

        await click("button:contains(Inbox)");
        assert.hasClass($("button:contains(Inbox)"), "o-active");
        assert.containsN($, ".o-mail-Message", 2);

        await click(".o-mail-Message:contains(not empty 1) [title='Expand']");
        await click(".o-mail-Message:contains(not empty 1) [title='Mark as Read']");
        assert.containsOnce($, ".o-mail-Message");
        assert.containsOnce($, ".o-mail-Message:contains(not empty 2)");

        await click("button:contains(History)");
        assert.hasClass($("button:contains(History)"), "o-active");
        assert.containsOnce($, ".o-mail-Message");
        assert.containsOnce($, ".o-mail-Message:contains(not empty 1)");
    }
);

QUnit.test('all messages in "Inbox" in "History" after marked all as read', async (assert) => {
    const pyEnv = await startServer();
    for (let i = 0; i < 40; i++) {
        const messageId = pyEnv["mail.message"].create({
            body: "not empty",
            needaction: true,
        });
        pyEnv["mail.notification"].create({
            mail_message_id: messageId,
            notification_type: "inbox",
            res_partner_id: pyEnv.currentPartnerId,
        });
    }
    const { openDiscuss } = await start();
    await openDiscuss();
    await click("button:contains(Mark all read)");
    assert.containsNone($, ".o-mail-Message");

    await click("button:contains(History)");
    $(".o-mail-Thread")[0].scrollTop = 0;
    await waitUntil(".o-mail-Message", 40);
});

QUnit.test("post a simple message", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === "/mail/message/post") {
                assert.step("message_post");
                assert.strictEqual(args.thread_model, "discuss.channel");
                assert.strictEqual(args.thread_id, channelId);
                assert.strictEqual(args.post_data.body, "Test");
                assert.strictEqual(args.post_data.message_type, "comment");
                assert.strictEqual(args.post_data.subtype_xmlid, "mail.mt_comment");
            }
        },
    });
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-mail-Thread:contains(There are no messages in this conversation.)");
    assert.containsNone($, ".o-mail-Message");
    assert.strictEqual($(".o-mail-Composer-input").val(), "");

    // insert some HTML in editable
    await insertText(".o-mail-Composer-input", "Test");
    assert.strictEqual($(".o-mail-Composer-input").val(), "Test");

    await click(".o-mail-Composer-send");
    assert.verifySteps(["message_post"]);
    assert.strictEqual($(".o-mail-Composer-input").val(), "");
    assert.containsOnce($, ".o-mail-Message");
    pyEnv["mail.message"].search([], { order: "id DESC" });
    const $message = $(".o-mail-Message");
    assert.containsOnce($, ".o-mail-Message:contains(Test)");
    assert.strictEqual($message.find(".o-mail-Message-author").text(), "Mitchell Admin");
    assert.strictEqual($message.find(".o-mail-Message-body").text(), "Test");
});

QUnit.test("starred: unstar all", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["mail.message"].create([
        { body: "not empty", starred_partner_ids: [pyEnv.currentPartnerId] },
        { body: "not empty", starred_partner_ids: [pyEnv.currentPartnerId] },
    ]);
    const { openDiscuss } = await start();
    await openDiscuss("mail.box_starred");
    assert.strictEqual($("button:contains(Starred) .badge").text(), "2");
    assert.containsN($, ".o-mail-Message", 2);
    let $unstarAll = $("button:contains(Unstar all)");
    assert.notOk($unstarAll[0].disabled);

    await click($unstarAll);
    assert.containsNone($, "button:contains(Starred) .badge");
    assert.containsNone($, ".o-mail-Message");
    $unstarAll = $("button:contains(Unstar all)");
    assert.ok($unstarAll[0].disabled);
});

QUnit.test("auto-focus composer on opening thread", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo User" });
    pyEnv["discuss.channel"].create([
        { name: "General" },
        {
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId }),
                Command.create({ partner_id: partnerId }),
            ],
            channel_type: "chat",
        },
    ]);
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, "button:contains(Inbox)");
    assert.hasClass($("button:contains(Inbox)"), "o-active");
    assert.containsOnce($, ".o-mail-DiscussCategoryItem:contains(General)");
    assert.doesNotHaveClass($(".o-mail-DiscussCategoryItem:contains(General)"), "o-active");
    assert.containsOnce($, ".o-mail-DiscussCategoryItem:contains(Demo User)");
    assert.doesNotHaveClass($(".o-mail-DiscussCategoryItem:contains(Demo User)"), "o-active");
    assert.containsNone($, ".o-mail-Composer");

    await click(".o-mail-DiscussCategoryItem:contains(General)");
    assert.hasClass($(".o-mail-DiscussCategoryItem:contains(General)"), "o-active");
    assert.containsOnce($, ".o-mail-Composer");
    assert.strictEqual(document.activeElement, $(".o-mail-Composer-input")[0]);

    await click(".o-mail-DiscussCategoryItem:contains(Demo User)");
    assert.hasClass($(".o-mail-DiscussCategoryItem:contains(Demo User)"), "o-active");
    assert.containsOnce($, ".o-mail-Composer");
    assert.strictEqual(document.activeElement, $(".o-mail-Composer-input")[0]);
});

QUnit.test(
    "receive new chat message: out of odoo focus (notification, channel)",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ channel_type: "chat" });
        const { env, openDiscuss } = await start({
            services: {
                presence: makeFakePresenceService({ isOdooFocused: () => false }),
            },
        });
        await openDiscuss();
        env.services.bus_service.addEventListener("set_title_part", ({ detail: payload }) => {
            assert.step("set_title_part");
            assert.strictEqual(payload.part, "_chat");
            assert.strictEqual(payload.title, "1 Message");
        });
        const channel = pyEnv["discuss.channel"].searchRead([["id", "=", channelId]])[0];
        // simulate receiving a new message with odoo focused
        pyEnv["bus.bus"]._sendone(channel, "discuss.channel/new_message", {
            id: channelId,
            message: {
                id: 126,
                model: "discuss.channel",
                res_id: channelId,
            },
        });
        await nextTick();
        assert.verifySteps(["set_title_part"]);
    }
);

QUnit.test("receive new chat message: out of odoo focus (notification, chat)", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "chat" });
    const { env, openDiscuss } = await start({
        services: {
            presence: makeFakePresenceService({ isOdooFocused: () => false }),
        },
    });
    await openDiscuss();
    env.services.bus_service.addEventListener("set_title_part", ({ detail: payload }) => {
        assert.step("set_title_part");
        assert.strictEqual(payload.part, "_chat");
        assert.strictEqual(payload.title, "1 Message");
    });
    const channel = pyEnv["discuss.channel"].searchRead([["id", "=", channelId]])[0];
    // simulate receiving a new message with odoo focused
    pyEnv["bus.bus"]._sendone(channel, "discuss.channel/new_message", {
        id: channelId,
        message: {
            id: 126,
            model: "discuss.channel",
            res_id: channelId,
        },
    });
    await nextTick();
    assert.verifySteps(["set_title_part"]);
});

QUnit.test("receive new chat messages: out of odoo focus (tab title)", async (assert) => {
    let step = 0;
    const pyEnv = await startServer();
    const [channelId_1, channelId_2] = pyEnv["discuss.channel"].create([
        { channel_type: "chat" },
        { channel_type: "chat" },
    ]);
    const { env, openDiscuss } = await start({
        services: {
            presence: makeFakePresenceService({ isOdooFocused: () => false }),
        },
    });
    await openDiscuss();
    env.services.bus_service.addEventListener("set_title_part", ({ detail: payload }) => {
        step++;
        assert.step("set_title_part");
        assert.strictEqual(payload.part, "_chat");
        if (step === 1) {
            assert.strictEqual(payload.title, "1 Message");
        }
        if (step === 2) {
            assert.strictEqual(payload.title, "2 Messages");
        }
        if (step === 3) {
            assert.strictEqual(payload.title, "3 Messages");
        }
    });
    const channel_1 = pyEnv["discuss.channel"].searchRead([["id", "=", channelId_1]])[0];
    // simulate receiving a new message in chat 1 with odoo focused
    pyEnv["bus.bus"]._sendone(channel_1, "discuss.channel/new_message", {
        id: channelId_1,
        message: {
            id: 126,
            model: "discuss.channel",
            res_id: channelId_1,
        },
    });
    await nextTick();
    assert.verifySteps(["set_title_part"]);

    const channel_2 = pyEnv["discuss.channel"].searchRead([["id", "=", channelId_2]])[0];
    // simulate receiving a new message in chat 2 with odoo focused
    pyEnv["bus.bus"]._sendone(channel_2, "discuss.channel/new_message", {
        id: channelId_2,
        message: {
            id: 127,
            model: "discuss.channel",
            res_id: channelId_2,
        },
    });
    await nextTick();
    assert.verifySteps(["set_title_part"]);

    // simulate receiving another new message in chat 2 with odoo focused
    pyEnv["bus.bus"]._sendone(channel_2, "discuss.channel/new_message", {
        id: channelId_2,
        message: {
            id: 128,
            model: "discuss.channel",
            res_id: channelId_2,
        },
    });
    await nextTick();
    await nextTick();
    assert.verifySteps(["set_title_part"]);
});

QUnit.test("should auto-pin chat when receiving a new DM", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ is_pinned: false, partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const { env, openDiscuss } = await start();
    await openDiscuss();
    assert.containsNone($, ".o-mail-DiscussCategoryItem:contains(Demo)");

    // simulate receiving the first message on channel 11
    await afterNextRender(() =>
        env.services.rpc("/mail/message/post", {
            context: { mockedUserId: userId },
            post_data: { body: "new message", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    assert.containsOnce($, ".o-mail-DiscussCategoryItem:contains(Demo)");
});

QUnit.test("'Add Users' button should be displayed in the topbar of channels", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, "button[title='Add Users']");
});

QUnit.test("'Add Users' button should be displayed in the topbar of chats", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Marc Demo" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, "button[title='Add Users']");
});

QUnit.test("'Add Users' button should be displayed in the topbar of groups", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "group",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, "button[title='Add Users']");
});

QUnit.test(
    "'Add Users' button should not be displayed in the topbar of mailboxes",
    async (assert) => {
        const { openDiscuss } = await start();
        await openDiscuss("mail.box_starred");
        assert.containsNone($, "button[title='Add Users']");
    }
);

QUnit.test(
    "Thread avatar image is displayed in top bar of channels of type 'channel' limited to a group",
    async (assert) => {
        const pyEnv = await startServer();
        const groupId = pyEnv["res.groups"].create({ name: "testGroup" });
        const channelId = pyEnv["discuss.channel"].create({
            channel_type: "channel",
            name: "string",
            group_public_id: groupId,
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.containsOnce($, ".o-mail-Discuss-header .o-mail-Discuss-threadAvatar");
    }
);

QUnit.test(
    "Thread avatar image is displayed in top bar of channels of type 'channel' not limited to any group",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({
            channel_type: "channel",
            name: "string",
            group_public_id: false,
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.containsOnce($, ".o-mail-Discuss-header .o-mail-Discuss-threadAvatar");
    }
);

QUnit.test(
    "Partner IM status is displayed as thread icon in top bar of channels of type 'chat'",
    async (assert) => {
        const pyEnv = await startServer();
        const [partnerId_1, partnerId_2, partnerId_3, partnerId_4] = pyEnv["res.partner"].create([
            { im_status: "online", name: "Michel Online" },
            { im_status: "offline", name: "Jacqueline Offline" },
            { im_status: "away", name: "Nabuchodonosor Idle" },
            { im_status: "im_partner", name: "Robert Fired" },
        ]);
        pyEnv["discuss.channel"].create([
            {
                channel_member_ids: [
                    Command.create({ partner_id: pyEnv.currentPartnerId }),
                    Command.create({ partner_id: partnerId_1 }),
                ],
                channel_type: "chat",
            },
            {
                channel_member_ids: [
                    Command.create({ partner_id: pyEnv.currentPartnerId }),
                    Command.create({ partner_id: partnerId_2 }),
                ],
                channel_type: "chat",
            },
            {
                channel_member_ids: [
                    Command.create({ partner_id: pyEnv.currentPartnerId }),
                    Command.create({ partner_id: partnerId_3 }),
                ],
                channel_type: "chat",
            },
            {
                channel_member_ids: [
                    Command.create({ partner_id: pyEnv.currentPartnerId }),
                    Command.create({ partner_id: partnerId_4 }),
                ],
                channel_type: "chat",
            },
            {
                channel_member_ids: [
                    Command.create({ partner_id: pyEnv.currentPartnerId }),
                    Command.create({ partner_id: TEST_USER_IDS.odoobotId }),
                ],
                channel_type: "chat",
            },
        ]);
        const { openDiscuss } = await start();
        await openDiscuss();
        await click(".o-mail-DiscussCategoryItem:contains('Michel Online')");
        assert.containsOnce($, ".o-mail-Discuss-header .o-mail-ImStatus [title='Online']");
        await click(".o-mail-DiscussCategoryItem:contains('Jacqueline Offline')");
        assert.containsOnce($, ".o-mail-Discuss-header .o-mail-ImStatus [title='Offline']");
        await click(".o-mail-DiscussCategoryItem:contains('Nabuchodonosor Idle')");
        assert.containsOnce($, ".o-mail-Discuss-header .o-mail-ImStatus [title='Idle']");
        await click(".o-mail-DiscussCategoryItem:contains('Robert Fired')");
        assert.containsOnce(
            $,
            ".o-mail-Discuss-header .o-mail-ImStatus [title='No IM status available']"
        );
        await click(".o-mail-DiscussCategoryItem:contains('OdooBot')");
        assert.containsOnce($, ".o-mail-Discuss-header .o-mail-ImStatus [title='Bot']");
    }
);

QUnit.test(
    "Thread avatar image is displayed in top bar of channels of type 'group'",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ channel_type: "group" });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.containsOnce($, ".o-mail-Discuss-header .o-mail-Discuss-threadAvatar");
    }
);

QUnit.test("Do not trigger chat name server update when it is unchanged", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "chat" });
    const { openDiscuss } = await start({
        mockRPC(route, args, originalRPC) {
            if (args.method === "channel_set_custom_name") {
                assert.step(args.method);
            }
            return originalRPC(route, args);
        },
    });
    await openDiscuss(channelId);
    await editInput(document.body, "input.o-mail-Discuss-threadName", "Mitchell Admin");
    await triggerEvent(document.body, "input.o-mail-Discuss-threadName", "keydown", {
        key: "Enter",
    });
    assert.verifySteps([]);
});

QUnit.test(
    "Do not trigger channel description server update when channel has no description and editing to empty description",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({
            create_uid: pyEnv.currentPartnerId,
            name: "General",
        });
        const { openDiscuss } = await start({
            mockRPC(route, args, originalRPC) {
                if (args.method === "channel_change_description") {
                    assert.step(args.method);
                }
                return originalRPC(route, args);
            },
        });
        await openDiscuss(channelId);
        await editInput(document.body, "input.o-mail-Discuss-threadDescription", "");
        await triggerEvent(document.body, "input.o-mail-Discuss-threadDescription", "keydown", {
            key: "Enter",
        });
        assert.verifySteps([]);
    }
);

QUnit.test("Channel is added to discuss after invitation", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_member_ids: [],
    });
    const userId = pyEnv["res.users"].create({ name: "Harry" });
    const { env, openDiscuss } = await start({
        services: {
            notification: makeFakeNotificationService((message) => assert.step(message)),
        },
    });
    await openDiscuss();
    assert.containsNone($, ".o-mail-DiscussCategoryItem:contains(General)");
    await afterNextRender(() => {
        env.services.orm.call("discuss.channel", "add_members", [[channelId]], {
            partner_ids: [pyEnv.currentPartnerId],
            context: { mockedUserId: userId },
        });
    });
    assert.containsOnce($, ".o-mail-DiscussCategoryItem:contains(General)");
    assert.verifySteps(["You have been invited to #General"]);
});

QUnit.test("Chat is added to discuss on other tab that the one that joined", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Jerry Golay" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const tab1 = await start({ asTab: true });
    const tab2 = await start({ asTab: true });
    await tab1.openDiscuss();
    await tab2.openDiscuss();
    await tab1.click(".o-mail-DiscussCategory-chat .o-mail-DiscussCategory-add");
    await tab1.insertText(".o-mail-ChannelSelector input", "Jer");
    await tab1.click(".o-mail-ChannelSelector-suggestion");
    await afterNextRender(() => triggerHotkey("Enter"));
    assert.containsOnce(tab1.target, ".o-mail-DiscussCategoryItem:contains(Jerry Golay)");
    assert.containsOnce(tab2.target, ".o-mail-DiscussCategoryItem:contains(Jerry Golay)");
});

QUnit.test("select another mailbox", async (assert) => {
    patchUiSize({ height: 360, width: 640 });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, ".o-mail-Discuss");
    assert.strictEqual($(".o-mail-Discuss-threadName").val(), "Inbox");
    assert.containsOnce($, "button:contains(Starred)");

    await click("button:contains(Starred)");
    assert.strictEqual($(".o-mail-Discuss-threadName").val(), "Starred");
});

QUnit.test(
    'auto-select "Inbox nav bar" when discuss had inbox as active thread',
    async (assert) => {
        patchUiSize({ height: 360, width: 640 });
        const { openDiscuss } = await start();
        await openDiscuss();
        assert.strictEqual($(".o-mail-Discuss-threadName").val(), "Inbox");
        assert.containsOnce($, ".o-mail-MessagingMenu-navbar:contains(Mailboxes) .fw-bolder");
        assert.containsOnce($, "button:contains(Inbox).o-active");
        assert.containsOnce($, "h4:contains(Congratulations, your inbox is empty)");
    }
);

QUnit.test(
    "composer should be focused automatically after clicking on the send button [REQUIRE FOCUS]",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ name: "test" });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        await insertText(".o-mail-Composer-input", "Dummy Message");
        await click(".o-mail-Composer-send");
        assert.strictEqual(document.activeElement, $(".o-mail-Composer-input")[0]);
    }
);

QUnit.test(
    "mark channel as seen if last message is visible when switching channels when the previous channel had a more recent last message than the current channel [REQUIRE FOCUS]",
    async (assert) => {
        const pyEnv = await startServer();
        const [channelId_1, channelId_2] = pyEnv["discuss.channel"].create([
            {
                channel_member_ids: [
                    [
                        0,
                        0,
                        {
                            message_unread_counter: 1,
                            partner_id: pyEnv.currentPartnerId,
                        },
                    ],
                ],
                name: "Bla",
            },
            {
                channel_member_ids: [
                    [
                        0,
                        0,
                        {
                            message_unread_counter: 1,
                            partner_id: pyEnv.currentPartnerId,
                        },
                    ],
                ],
                name: "Blu",
            },
        ]);
        pyEnv["mail.message"].create([
            {
                body: "oldest message",
                model: "discuss.channel",
                res_id: channelId_1,
            },
            {
                body: "newest message",
                model: "discuss.channel",
                res_id: channelId_2,
            },
        ]);
        const { openDiscuss } = await start();
        await openDiscuss(channelId_2);
        await click("button:contains(Bla)");
        assert.containsNone($, ".o-unread");
    }
);

QUnit.test(
    "warning on send with shortcut when attempting to post message with still-uploading attachments",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ name: "test" });
        const { openDiscuss } = await start({
            async mockRPC(route) {
                if (route === "/mail/attachment/upload") {
                    // simulates attachment is never finished uploading
                    await new Promise(() => {});
                }
            },
            services: {
                notification: makeFakeNotificationService((message, options) => {
                    assert.strictEqual(message, "Please wait while the file is uploading.");
                    assert.strictEqual(options.type, "warning", "notification should be a warning");
                    assert.step("notification");
                }),
            },
        });
        await openDiscuss(channelId);
        const file = await createFile({
            content: "hello, world",
            contentType: "text/plain",
            name: "text.txt",
        });
        await afterNextRender(() =>
            editInput(document.body, ".o-mail-Composer input[type=file]", [file])
        );
        assert.containsOnce($, ".o-mail-AttachmentCard");
        assert.containsOnce($, ".o-mail-AttachmentCard.o-isUploading");
        assert.containsOnce($, ".o-mail-Composer-send");

        // Try to send message
        triggerHotkey("Enter");
        assert.verifySteps(["notification"]);
    }
);

QUnit.test("new messages separator [REQUIRE FOCUS]", async (assert) => {
    // this test requires several messages so that the last message is not
    // visible. This is necessary in order to display 'new messages' and not
    // remove from DOM right away from seeing last message.
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Foreigner partner" });
    const userId = pyEnv["res.users"].create({
        name: "Foreigner user",
        partner_id: partnerId,
    });
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    let lastMessageId;
    for (let i = 1; i <= 25; i++) {
        lastMessageId = pyEnv["mail.message"].create({
            body: "not empty",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    const [memberId] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", pyEnv.currentPartnerId],
    ]);
    pyEnv["discuss.channel.member"].write([memberId], { seen_message_id: lastMessageId });
    const { env, openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsN($, ".o-mail-Message", 25);
    assert.containsNone($, "hr + span:contains(New messages)");

    $(".o-mail-Discuss-content .o-mail-Thread")[0].scrollTop = 0;
    // composer is focused by default, we remove that focus
    $(".o-mail-Composer-input")[0].blur();
    // simulate receiving a message
    await afterNextRender(async () =>
        env.services.rpc("/mail/message/post", {
            context: { mockedUserId: userId },
            post_data: { body: "hu", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    assert.containsN($, ".o-mail-Message", 26);
    assert.containsOnce($, "hr + span:contains(New messages)");
    const messageList = $(".o-mail-Discuss-content .o-mail-Thread")[0];
    messageList.scrollTop = messageList.scrollHeight - messageList.clientHeight;
    assert.containsOnce($, "hr + span:contains(New messages)");

    await afterNextRender(() => $(".o-mail-Composer-input")[0].focus());
    assert.containsNone($, "hr + span:contains(New messages)");
});

QUnit.test("failure on loading messages should display error", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "General",
    });
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === "/discuss/channel/messages") {
                return Promise.reject();
            }
        },
    });
    await openDiscuss(channelId, { waitUntilMessagesLoaded: false });
    assert.containsOnce(
        $,
        ".o-mail-Thread-error:contains(An error occurred while fetching messages.)"
    );
});

QUnit.test("failure on loading messages should prompt retry button", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "General",
    });
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === "/discuss/channel/messages") {
                return Promise.reject();
            }
        },
    });
    await openDiscuss(channelId, { waitUntilMessagesLoaded: false });
    assert.containsOnce($, "button:contains(Click here to retry)");
});

QUnit.test(
    "failure on loading more messages should not alter message list display",
    async (assert) => {
        // first call needs to be successful as it is the initial loading of messages
        // second call comes from load more and needs to fail in order to show the error alert
        // any later call should work so that retry button and load more clicks would now work
        let messageFetchShouldFail = false;
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({
            channel_type: "channel",
            name: "General",
        });
        pyEnv["mail.message"].create(
            [...Array(60).keys()].map(() => {
                return {
                    body: "coucou",
                    model: "discuss.channel",
                    res_id: channelId,
                };
            })
        );
        const { openDiscuss } = await start({
            async mockRPC(route, args) {
                if (route === "/discuss/channel/messages" && messageFetchShouldFail) {
                    return Promise.reject();
                }
            },
        });
        await openDiscuss(channelId);
        messageFetchShouldFail = true;
        await click("button:contains(Load More)");
        assert.containsN($, ".o-mail-Message", 30);
    }
);

QUnit.test(
    "failure on loading more messages should display error and prompt retry button",
    async (assert) => {
        // first call needs to be successful as it is the initial loading of messages
        // second call comes from load more and needs to fail in order to show the error alert
        // any later call should work so that retry button and load more clicks would now work
        let messageFetchShouldFail = false;
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({
            channel_type: "channel",
            name: "General",
        });
        pyEnv["mail.message"].create(
            [...Array(60).keys()].map(() => {
                return {
                    body: "coucou",
                    model: "discuss.channel",
                    res_id: channelId,
                };
            })
        );
        const { openDiscuss } = await start({
            async mockRPC(route, args) {
                if (route === "/discuss/channel/messages" && messageFetchShouldFail) {
                    return Promise.reject();
                }
            },
        });
        await openDiscuss(channelId);
        messageFetchShouldFail = true;
        await click("button:contains(Load More)");
        assert.containsOnce(
            $,
            ".o-mail-Thread-error:contains(An error occurred while fetching messages.)"
        );
        assert.containsOnce($, "button:contains(Click here to retry)");
        assert.containsNone($, "button:contains(Load More)");
    }
);

QUnit.test(
    "Retry loading more messages on failed load more messages should load more messages",
    async (assert) => {
        // first call needs to be successful as it is the initial loading of messages
        // second call comes from load more and needs to fail in order to show the error alert
        // any later call should work so that retry button and load more clicks would now work
        let messageFetchShouldFail = false;
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({
            channel_type: "channel",
            name: "General",
        });
        pyEnv["mail.message"].create(
            [...Array(90).keys()].map(() => {
                return {
                    body: "coucou",
                    model: "discuss.channel",
                    res_id: channelId,
                };
            })
        );
        const { openDiscuss } = await start({
            async mockRPC(route, args) {
                if (route === "/discuss/channel/messages") {
                    if (messageFetchShouldFail) {
                        return Promise.reject();
                    }
                }
            },
        });
        await openDiscuss(channelId);
        messageFetchShouldFail = true;
        await click("button:contains(Load More)");
        messageFetchShouldFail = false;
        await click("button:contains(Click here to retry)");
        assert.containsN($, ".o-mail-Message", 60);
    }
);

QUnit.test("composer state: attachments save and restore", async (assert) => {
    const pyEnv = await startServer();
    const [channelId] = pyEnv["discuss.channel"].create([{ name: "General" }, { name: "Special" }]);
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    // Add attachment in a message for #general
    await afterNextRender(async () => {
        const file = await createFile({
            content: "hello, world",
            contentType: "text/plain",
            name: "text.txt",
        });
        editInput(document.body, ".o-mail-Composer input[type=file]", [file]);
    });
    // Switch to #special
    await click("button:contains(Special)");
    // Attach files in a message for #special
    const files = [
        await createFile({
            content: "hello2, world",
            contentType: "text/plain",
            name: "text2.txt",
        }),
        await createFile({
            content: "hello3, world",
            contentType: "text/plain",
            name: "text3.txt",
        }),
        await createFile({
            content: "hello4, world",
            contentType: "text/plain",
            name: "text4.txt",
        }),
    ];
    await afterNextRender(() =>
        editInput(document.body, ".o-mail-Composer input[type=file]", files)
    );
    // Switch back to #general
    await click("button:contains(General)");
    // Check attachment is reloaded
    assert.containsOnce($, ".o-mail-Composer .o-mail-AttachmentCard");
    assert.containsOnce($, ".o-mail-AttachmentCard:contains(text.txt)");

    // Switch back to #special
    await click("button:contains(Special)");
    assert.containsN($, ".o-mail-Composer .o-mail-AttachmentCard", 3);
    assert.containsOnce($, ".o-mail-AttachmentCard:contains(text2.txt)");
    assert.containsOnce($, ".o-mail-AttachmentCard:contains(text3.txt)");
    assert.containsOnce($, ".o-mail-AttachmentCard:contains(text4.txt)");
});

QUnit.test(
    "sidebar: cannot unpin channel group_based_subscription: mandatorily pinned",
    async (assert) => {
        const pyEnv = await startServer();
        pyEnv["discuss.channel"].create({
            name: "General",
            channel_member_ids: [
                Command.create({ is_pinned: false, partner_id: pyEnv.currentPartnerId }),
            ],
            group_based_subscription: true,
        });
        const { openDiscuss } = await start();
        await openDiscuss();
        assert.containsOnce($, "button:contains(General)");
        assert.containsNone($, "div[title='Leave this channel']");
    }
);

QUnit.test("restore thread scroll position", async (assert) => {
    const pyEnv = await startServer();
    const [channelId_1, channelId_2] = pyEnv["discuss.channel"].create([
        { name: "Channel1" },
        { name: "Channel2" },
    ]);
    for (let i = 1; i <= 25; i++) {
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "discuss.channel",
            res_id: channelId_1,
        });
    }
    for (let i = 1; i <= 24; i++) {
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "discuss.channel",
            res_id: channelId_2,
        });
    }
    const { openDiscuss } = await start();
    await openDiscuss(channelId_1);
    assert.containsN($, ".o-mail-Message", 25);
    let thread = $(".o-mail-Thread")[0];
    assert.ok(isScrolledToBottom(thread));

    $(".o-mail-Thread")[0].scrollTop = 0;
    assert.strictEqual($(".o-mail-Thread")[0].scrollTop, 0);

    // Ensure scrollIntoView of channel 2 has enough time to complete before
    // going back to channel 1. Await is needed to prevent the scrollIntoView
    // initially planned for channel 2 to actually apply on channel 1.
    // task-2333535
    await click("button:contains(Channel2)");
    assert.containsN($, ".o-mail-Message", 24);

    await click("button:contains(Channel1)");
    assert.strictEqual($(".o-mail-Thread")[0].scrollTop, 0);

    await click("button:contains(Channel2)");
    thread = $(".o-mail-Thread")[0];
    assert.ok(isScrolledToBottom(thread));
});

QUnit.test("Message shows up even if channel data is incomplete", async (assert) => {
    const { env, openDiscuss, pyEnv } = await start();
    await openDiscuss();
    const correspondentUserId = pyEnv["res.users"].create({ name: "Albert" });
    const correspondentPartnerId = pyEnv["res.partner"].create({
        name: "Albert",
        user_ids: [correspondentUserId],
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            [
                0,
                0,
                {
                    is_pinned: true,
                    partner_id: pyEnv.currentPartnerId,
                },
            ],
            Command.create({ partner_id: correspondentPartnerId }),
        ],
        channel_type: "chat",
    });
    await env.services.rpc("/discuss/channel/notify_typing", {
        context: { mockedPartnerId: correspondentPartnerId },
        is_typing: true,
        channel_id: channelId,
    });
    await afterNextRender(
        async () =>
            await env.services.rpc("/mail/message/post", {
                context: { mockedUserId: correspondentUserId },
                post_data: { body: "hello world", message_type: "comment" },
                thread_id: channelId,
                thread_model: "discuss.channel",
            })
    );
    await click(".o-mail-DiscussCategory-chat + .o-mail-DiscussCategoryItem:contains(Albert)");
    assert.containsOnce($, ".o-mail-Message:contains(hello world)");
});

QUnit.test("Create a direct message channel when clicking on start a meeting", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "General",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("button:contains(Start a meeting)");
    assert.containsOnce($, ".o-mail-DiscussCategoryItem:contains(Mitchell Admin)");
    assert.containsOnce($, ".o-mail-Call");
    await waitUntil(".o-discuss-ChannelInvitation");
    assert.containsOnce($, ".o-discuss-ChannelInvitation");
});

QUnit.test(
    "Correct breadcrumb when open discuss from chat window then see settings",
    async (assert) => {
        const pyEnv = await startServer();
        pyEnv["discuss.channel"].create({ name: "General" });
        await start();
        await click(".o_main_navbar i[aria-label='Messages']");
        await click(".o-mail-NotificationItem:contains(General)");
        await click("[title='More actions']");
        await click("[title='Open in Discuss']");
        await click(".o-mail-DiscussCategoryItem:contains(General) [title='Channel settings']");
        assert.strictEqual($(".o_breadcrumb").text(), "DiscussGeneral");
    }
);
