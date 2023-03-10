/** @odoo-module **/

import { TEST_USER_IDS } from "@bus/../tests/helpers/test_constants";
import { patchUiSize } from "@mail/../tests/helpers/patch_ui_size";

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
    assert.containsOnce($, ".o-DiscussSidebar");
    assert.containsOnce($, "h4:contains(Congratulations, your inbox is empty)");
    assert.verifySteps([
        "/mail/init_messaging",
        "/mail/load_message_failures",
        "/mail/inbox/messages",
    ]);
});

QUnit.test("can change the thread name of #general", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    const { openDiscuss } = await start({
        mockRPC(route, params) {
            if (route === "/web/dataset/call_kw/mail.channel/channel_rename") {
                assert.step(route);
            }
        },
    });
    await openDiscuss(channelId);
    assert.containsOnce($, "input.o-Discuss-threadName");
    const $name = $("input.o-Discuss-threadName");

    click($name).catch(() => {});
    assert.strictEqual($name.val(), "general");
    await editInput(document.body, "input.o-Discuss-threadName", "special");
    await triggerEvent(document.body, "input.o-Discuss-threadName", "keydown", {
        key: "Enter",
    });
    assert.strictEqual($name.val(), "special");
    assert.verifySteps(["/web/dataset/call_kw/mail.channel/channel_rename"]);
});

QUnit.test("can change the thread description of #general", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        name: "general",
        channel_type: "channel",
        description: "General announcements...",
    });
    const { openDiscuss } = await start({
        mockRPC(route, params) {
            if (route === "/web/dataset/call_kw/mail.channel/channel_change_description") {
                assert.step(route);
            }
        },
    });
    await openDiscuss(channelId);
    assert.containsOnce($, "input.o-Discuss-threadDescription");
    const $description = $("input.o-Discuss-threadDescription");

    click($description).then(() => {});
    assert.strictEqual($description.val(), "General announcements...");
    await editInput(document.body, "input.o-Discuss-threadDescription", "I want a burger today!");
    await triggerEvent(document.body, "input.o-Discuss-threadDescription", "keydown", {
        key: "Enter",
    });
    assert.strictEqual($description.val(), "I want a burger today!");
    assert.verifySteps(["/web/dataset/call_kw/mail.channel/channel_change_description"]);
});

QUnit.test("can create a new channel [REQUIRE FOCUS]", async (assert) => {
    await startServer();
    const { openDiscuss } = await start({
        mockRPC(route, params) {
            if (
                route.startsWith("/mail") ||
                [
                    "/web/dataset/call_kw/mail.channel/search_read",
                    "/web/dataset/call_kw/mail.channel/channel_create",
                ].includes(route)
            ) {
                assert.step(route);
            }
        },
    });
    await openDiscuss();
    assert.containsNone($, ".o-DiscussCategoryItem");

    await click(".o-DiscussSidebar i[title='Add or join a channel']");
    await afterNextRender(() => editInput(document.body, ".o-ChannelSelector input", "abc"));
    await click(".o-ChannelSelector-suggestion");
    assert.containsOnce($, ".o-DiscussCategoryItem");
    assert.containsNone($, ".o-Discuss-content .o-Message");
    assert.verifySteps([
        "/mail/init_messaging",
        "/mail/load_message_failures",
        "/mail/inbox/messages",
        "/web/dataset/call_kw/mail.channel/search_read",
        "/web/dataset/call_kw/mail.channel/channel_create",
        "/mail/channel/members",
        "/mail/channel/messages",
        "/mail/channel/set_last_seen_message",
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
        assert.containsNone($, ".o-DiscussCategoryItem");

        await click("i[title='Start a conversation']");
        await afterNextRender(() => editInput(document.body, ".o-ChannelSelector input", "mario"));
        await click(".o-ChannelSelector-suggestion");
        assert.containsOnce($, ".o-ChannelSelector span[title='Mario']");
        assert.containsNone($, ".o-DiscussCategoryItem");

        await triggerEvent(document.body, ".o-ChannelSelector input", "keydown", {
            key: "Backspace",
        });
        assert.containsNone($, ".o-ChannelSelector span[title='Mario']");

        await afterNextRender(() => editInput(document.body, ".o-ChannelSelector input", "mario"));
        await triggerEvent(document.body, ".o-ChannelSelector input", "keydown", {
            key: "Enter",
        });
        assert.containsOnce($, ".o-ChannelSelector span[title='Mario']");
        assert.containsNone($, ".o-DiscussCategoryItem");
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
                ["/web/dataset/call_kw/mail.channel/channel_get"].includes(route)
            ) {
                assert.step(route);
            }
            if (route === "/web/dataset/call_kw/mail.channel/channel_get") {
                assert.equal(params.kwargs.partners_to[0], partnerId);
            }
        },
    });
    await openDiscuss();
    assert.containsNone($, ".o-DiscussCategoryItem");

    await click(".o-DiscussSidebar i[title='Start a conversation']");
    await afterNextRender(() => editInput(document.body, ".o-ChannelSelector input", "mario"));
    await click(".o-ChannelSelector-suggestion");
    await triggerEvent(document.body, ".o-ChannelSelector input", "keydown", {
        key: "Enter",
    });
    assert.containsOnce($, ".o-DiscussCategoryItem");
    assert.containsNone($, ".o-Message");
    assert.verifySteps([
        "/mail/init_messaging",
        "/mail/load_message_failures",
        "/mail/inbox/messages",
        "/web/dataset/call_kw/mail.channel/channel_get",
        "/mail/channel/messages",
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
    assert.containsNone($, ".o-DiscussCategoryItem");
    await click(".o-DiscussSidebar i[title='Start a conversation']");
    await insertText(".o-ChannelSelector input", "Mario");
    await click(".o-ChannelSelector-suggestion");
    await insertText(".o-ChannelSelector input", "Luigi");
    await click(".o-ChannelSelector-suggestion");
    await triggerEvent(document.body, ".o-ChannelSelector input", "keydown", {
        key: "Enter",
    });
    assert.containsN($, ".o-DiscussCategoryItem", 1);
    assert.containsNone($, ".o-Message");
});

QUnit.test("Message following a notification should not be squashed", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        author_id: pyEnv.currentPartnerId,
        body: '<div class="o_mail_notification">created <a href="#" class="o_channel_redirect">#general</a></div>',
        model: "mail.channel",
        res_id: channelId,
        message_type: "notification",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await editInput(document.body, ".o-Composer-input", "Hello world!");
    await click(".o-Composer button:contains(Send)");
    assert.containsOnce($, ".o-Message-sidebar .o-Message-avatarContainer");
});

QUnit.test("Posting message should transform links.", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await insertText(".o-Composer-input", "test https://www.odoo.com/");
    await click(".o-Composer-send");
    assert.containsOnce($, "a[href='https://www.odoo.com/']");
});

QUnit.test("Posting message should transform relevant data to emoji.", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        name: "general",
        channel_type: "channel",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await insertText(".o-Composer-input", "test :P :laughing:");
    await click(".o-Composer-send");
    assert.equal($(".o-Message-body").text(), "test 😛 😆");
});

QUnit.test(
    "posting a message immediately after another one is displayed in 'simple' mode (squashed)",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({
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
        await editInput(document.body, ".o-Composer-input", "abc");
        await click(".o-Composer button:contains(Send)");

        // write another message, but /mail/message/post is delayed by promise
        flag = true;
        await editInput(document.body, ".o-Composer-input", "def");
        await click(".o-Composer button:contains(Send)");
        assert.containsN($, ".o-Message", 2);
        assert.containsN($, ".o-Message-header", 1); // just 1, because 2nd message is squashed
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
    assert.containsOnce($, ".o-Message-sidebar .o-Message-avatarContainer img");
    await click(".o-Message-sidebar .o-Message-avatarContainer img");
    assert.containsOnce($, ".o-ChatWindow-name");
    assert.ok($(".o-ChatWindow-name").text().includes("testPartner"));
});

QUnit.test("Can use channel command /who", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        channel_type: "channel",
        name: "my-channel",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await insertText(".o-Composer-input", "/who");
    await click(".o-Composer button:contains(Send)");
    assert.strictEqual($(".o_mail_notification").text(), "You are alone in this channel.");
});

QUnit.test("sidebar: chat im_status rendering", async (assert) => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2, partnerId_3] = pyEnv["res.partner"].create([
        { im_status: "offline", name: "Partner1" },
        { im_status: "online", name: "Partner2" },
        { im_status: "away", name: "Partner3" },
    ]);
    pyEnv["mail.channel"].create([
        {
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: partnerId_1 }],
            ],
            channel_type: "chat",
        },
        {
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: partnerId_2 }],
            ],
            channel_type: "chat",
        },
        {
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: partnerId_3 }],
            ],
            channel_type: "chat",
        },
    ]);
    const { openDiscuss } = await start({ hasTimeControl: true });
    await openDiscuss();
    assert.containsN($, ".o-DiscussCategoryItem-threadIcon", 3);
    const chat1 = $(".o-DiscussCategoryItem")[0];
    const chat2 = $(".o-DiscussCategoryItem")[1];
    const chat3 = $(".o-DiscussCategoryItem")[2];
    assert.strictEqual(chat1.textContent, "Partner1");
    assert.strictEqual(chat2.textContent, "Partner2");
    assert.strictEqual(chat3.textContent, "Partner3");
    assert.containsOnce(chat1, ".o-ThreadIcon div[title='Offline']");
    assert.containsOnce(chat2, ".o-ThreadIcon-online");
    assert.containsOnce(chat3, ".o-ThreadIcon div[title='Away']");
});

QUnit.test("No load more when fetch below fetch limit of 30", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "general" });
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["res.partner"].create({});
    for (let i = 28; i >= 0; i--) {
        pyEnv["mail.message"].create({
            author_id: partnerId,
            body: "not empty",
            date: "2019-04-20 10:00:00",
            model: "mail.channel",
            res_id: channelId,
        });
    }
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === "/mail/channel/messages") {
                assert.strictEqual(args.limit, 30);
            }
        },
    });
    await openDiscuss(channelId);
    assert.containsN($, ".o-Message", 29);
    assert.containsNone($, "button:contains(Load more)");
});

QUnit.test("show date separator above mesages of similar date", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "general" });
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["res.partner"].create({});
    for (let i = 28; i >= 0; i--) {
        pyEnv["mail.message"].create({
            author_id: partnerId,
            body: "not empty",
            date: "2019-04-20 10:00:00",
            model: "mail.channel",
            res_id: channelId,
        });
    }
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.ok(
        $("hr + span:contains(April 20, 2019) + hr").offset().top < $(".o-Message").offset().top,
        "should have a single date separator above all the messages" // to check: may be client timezone dependent
    );
});

QUnit.test("sidebar: chat custom name", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Marc Demo" });
    pyEnv["mail.channel"].create({
        channel_member_ids: [
            [0, 0, { custom_channel_name: "Marc", partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId }],
        ],
        channel_type: "chat",
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.strictEqual($(".o-DiscussCategoryItem span").text(), "Marc");
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
    assert.containsOnce($, ".o-Message");
    assert.containsOnce($, ".o-Message-header:contains(on Refactoring)");

    await click("i[aria-label='Reply']");
    assert.hasClass($(".o-Message"), "o-selected");
    assert.containsOnce($, ".o-Composer");
    assert.containsOnce($, ".o-Composer-coreHeader:contains(on: Refactoring)");
    assert.strictEqual(document.activeElement, $(".o-Composer-input")[0]);

    await insertText(".o-Composer-input", "Test");
    await click(".o-Composer-send");
    assert.verifySteps(["message_post"]);
    assert.containsNone($, ".o-Composer");
    assert.containsOnce($, ".o-Message");
    assert.containsOnce($, ".o-Message:contains(Test)");
    assert.doesNotHaveClass($(".o-Message"), "o-selected");
});

QUnit.test("Can reply to starred message", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "RandomName" });
    pyEnv["mail.message"].create({
        body: "not empty",
        model: "mail.channel",
        starred_partner_ids: [pyEnv.currentPartnerId],
        res_id: channelId,
    });
    const { openDiscuss } = await start({
        services: {
            notification: makeFakeNotificationService((message) => assert.step(message)),
        },
    });
    await openDiscuss("mail.box_starred");
    await click("i[aria-label='Reply']");
    assert.containsOnce($, ".o-Composer-coreHeader:contains('RandomName')");
    await insertText(".o-Composer-input", "abc");
    await click(".o-Composer-send");
    assert.verifySteps(['Message posted on "RandomName"']);
    assert.containsOnce($, ".o-Message");
});

QUnit.test("Can reply to history message", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "RandomName" });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "mail.channel",
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
    await click("i[aria-label='Reply']");
    assert.containsOnce($, ".o-Composer-coreHeader:contains('RandomName')");
    await insertText(".o-Composer-input", "abc");
    await click(".o-Composer-send");
    assert.verifySteps(['Message posted on "RandomName"']);
    assert.containsOnce($, ".o-Message");
});

QUnit.test("receive new needaction messages", async (assert) => {
    const { openDiscuss, pyEnv } = await start();
    await openDiscuss();
    assert.containsOnce($, "button:contains(Inbox)");
    assert.hasClass($("button:contains(Inbox)"), "o-active");
    assert.containsNone($, "button:contains(Inbox) .badge");
    assert.containsNone($, ".o-Thread .o-Message");

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
    assert.containsOnce($, ".o-Message");
    assert.containsOnce($, ".o-Message:contains(not empty 1)");

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
    assert.containsN($, ".o-Message", 2);
    assert.containsOnce($, ".o-Message:contains(not empty 1)");
    assert.containsOnce($, ".o-Message:contains(not empty 2)");
});

QUnit.test("basic rendering", async (assert) => {
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, ".o-DiscussSidebar");
    assert.containsOnce($, ".o-Discuss-content");
    assert.containsOnce($, ".o-Discuss-content .o-Thread");
});

QUnit.test("basic rendering: sidebar", async (assert) => {
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, ".o-DiscussSidebar button:contains(Inbox)");
    assert.containsOnce($, ".o-DiscussSidebar button:contains(Starred)");
    assert.containsOnce($, ".o-DiscussSidebar button:contains(History)");
    assert.containsN($, ".o-DiscussCategory", 2);
    assert.containsOnce($, ".o-DiscussCategory-channel");
    assert.containsOnce($, ".o-DiscussCategory-chat");
    assert.strictEqual($(".o-DiscussCategory-channel").text(), "Channels");
    assert.strictEqual($(".o-DiscussCategory-chat").text(), "Direct messages");
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
    assert.containsOnce($, ".o-DiscussCategory-channel .o-DiscussCategory-add");
    assert.hasAttrValue(
        $(".o-DiscussCategory-channel .o-DiscussCategory-add")[0],
        "title",
        "Add or join a channel"
    );
    await click(".o-DiscussCategory-channel .o-DiscussCategory-add");
    assert.containsOnce($, ".o-ChannelSelector");
    assert.containsOnce($, ".o-ChannelSelector input[placeholder='Add or join a channel']");
});

QUnit.test("sidebar: basic channel rendering", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["mail.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, ".o-DiscussCategoryItem");
    assert.strictEqual($(".o-DiscussCategoryItem").text(), "General");
    assert.containsOnce($(".o-DiscussCategoryItem"), "img[data-alt='Thread Image']");
    assert.containsOnce($(".o-DiscussCategoryItem"), ".o-DiscussCategoryItem-commands");
    assert.hasClass($(".o-DiscussCategoryItem .o-DiscussCategoryItem-commands"), "d-none");
    assert.containsOnce(
        $(".o-DiscussCategoryItem .o-DiscussCategoryItem-commands"),
        "i[title='Channel settings']"
    );
    assert.containsOnce(
        $(".o-DiscussCategoryItem .o-DiscussCategoryItem-commands"),
        "div[title='Leave this channel']"
    );
});

QUnit.test("channel become active", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["mail.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, ".o-DiscussCategoryItem");
    assert.containsNone($, ".o-DiscussCategoryItem.o-active");
    await click(".o-DiscussCategoryItem");
    assert.containsOnce($, ".o-DiscussCategoryItem.o-active");
});

QUnit.test("channel become active - show composer in discuss content", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["mail.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss();
    await click(".o-DiscussCategoryItem");
    assert.containsOnce($, ".o-Thread");
    assert.containsOnce($, ".o-Composer");
});

QUnit.test("sidebar: channel rendering with needaction counter", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "general" });
    const messageId = pyEnv["mail.message"].create({
        body: "not empty",
        model: "mail.channel",
        res_id: channelId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_type: "inbox",
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, ".o-DiscussCategoryItem:contains(general)");
    assert.containsOnce($, ".o-DiscussCategoryItem:contains(general) .badge:contains(1)");
});

QUnit.test("sidebar: chat rendering with unread counter", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["mail.channel"].create({
        channel_member_ids: [
            [0, 0, { message_unread_counter: 100, partner_id: pyEnv.currentPartnerId }],
        ],
        channel_type: "chat",
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, ".o-DiscussCategoryItem .badge:contains(100)");
    assert.containsNone(
        $,
        ".o-DiscussCategoryItem .o-DiscussCategoryItem-commands:contains(Unpin Conversation)"
    );
});

QUnit.test("initially load messages from inbox", async (assert) => {
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === "/mail/inbox/messages") {
                assert.step("/mail/channel/messages");
                assert.strictEqual(args.limit, 30);
            }
        },
    });
    await openDiscuss();
    assert.verifySteps(["/mail/channel/messages"]);
});

QUnit.test("default active id on mailbox", async (assert) => {
    const { openDiscuss } = await start();
    await openDiscuss("mail.box_starred");
    assert.hasClass($("button:contains(Starred)"), "o-active");
});

QUnit.test("basic top bar rendering", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["mail.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.strictEqual($(".o-Discuss-threadName").val(), "Inbox");
    const $markAllRead = $("button:contains(Mark all read)");
    assert.isVisible($markAllRead);
    assert.ok($markAllRead[0].disabled);

    await click("button:contains(Starred)");
    assert.strictEqual($(".o-Discuss-threadName").val(), "Starred");
    const $unstarAll = $("button:contains(Unstar all)");
    assert.isVisible($unstarAll);
    assert.ok($unstarAll[0].disabled);

    await click(".o-DiscussCategoryItem:contains(General)");
    assert.strictEqual($(".o-Discuss-threadName").val(), "General");
    assert.isVisible($(".o-Discuss-header button[title='Add Users']"));
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
    assert.containsOnce($, ".o-Message");
    const $message = $(".o-Message");
    assert.containsOnce($message, ".o-Message-header:contains(on Refactoring)");
    assert.containsN($message, ".o-Message-actions i", 4);
    assert.containsOnce($message, "i[aria-label='Add a Reaction']");
    assert.containsOnce($message, "i[aria-label='Mark as Todo']");
    assert.containsOnce($message, "i[aria-label='Reply']");
    assert.containsOnce($message, "i[aria-label='Mark as Read']");
});

QUnit.test('messages marked as read move to "History" mailbox', async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "other-disco" });
    const [messageId_1, messageId_2] = pyEnv["mail.message"].create([
        {
            body: "not empty",
            model: "mail.channel",
            needaction: true,
            res_id: channelId,
        },
        {
            body: "not empty",
            model: "mail.channel",
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
    assert.containsOnce($, ".o-Thread:contains(No history messages)");

    await click("button:contains(Inbox)");
    assert.hasClass($("button:contains(Inbox)"), "o-active");
    assert.containsNone($, ".o-Thread:contains(Congratulations, your inbox is empty)");
    assert.containsN($, ".o-Thread .o-Message", 2);

    await click("button:contains(Mark all read)");
    assert.hasClass($("button:contains(Inbox)"), "o-active");
    assert.containsOnce($, ".o-Thread:contains(Congratulations, your inbox is empty)");

    await click("button:contains(History)");
    assert.hasClass($("button:contains(History)"), "o-active");
    assert.containsNone($, ".o-Thread:contains(No history messages)");
    assert.containsN($, ".o-Thread .o-Message", 2);
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
        assert.containsOnce($, ".o-Thread:contains(No history messages)");

        await click("button:contains(Inbox)");
        assert.hasClass($("button:contains(Inbox)"), "o-active");
        assert.containsN($, ".o-Message", 2);

        await click(".o-Message:contains(not empty 1) i[aria-label='Mark as Read']");
        assert.containsOnce($, ".o-Message");
        assert.containsOnce($, ".o-Message:contains(not empty 2)");

        await click("button:contains(History)");
        assert.hasClass($("button:contains(History)"), "o-active");
        assert.containsOnce($, ".o-Message");
        assert.containsOnce($, ".o-Message:contains(not empty 1)");
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
    assert.containsNone($, ".o-Message");

    await click("button:contains(History)");
    $(".o-Thread")[0].scrollTop = 0;
    await waitUntil(".o-Message", 40);
});

QUnit.test("post a simple message", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "general" });
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === "/mail/message/post") {
                assert.step("message_post");
                assert.strictEqual(args.thread_model, "mail.channel");
                assert.strictEqual(args.thread_id, channelId);
                assert.strictEqual(args.post_data.body, "Test");
                assert.strictEqual(args.post_data.message_type, "comment");
                assert.strictEqual(args.post_data.subtype_xmlid, "mail.mt_comment");
            }
        },
    });
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-Thread:contains(There are no messages in this conversation.)");
    assert.containsNone($, ".o-Message");
    assert.strictEqual($(".o-Composer-input").val(), "");

    // insert some HTML in editable
    await insertText(".o-Composer-input", "Test");
    assert.strictEqual($(".o-Composer-input").val(), "Test");

    await click(".o-Composer-send");
    assert.verifySteps(["message_post"]);
    assert.strictEqual($(".o-Composer-input").val(), "");
    assert.containsOnce($, ".o-Message");
    pyEnv["mail.message"].search([], { order: "id DESC" });
    const $message = $(".o-Message");
    assert.containsOnce($, ".o-Message:contains(Test)");
    assert.strictEqual($message.find(".o-Message-author").text(), "Mitchell Admin");
    assert.strictEqual($message.find(".o-Message-body").text(), "Test");
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
    assert.containsN($, ".o-Message", 2);
    let $unstarAll = $("button:contains(Unstar all)");
    assert.notOk($unstarAll[0].disabled);

    await click($unstarAll);
    assert.containsNone($, "button:contains(Starred) .badge");
    assert.containsNone($, ".o-Message");
    $unstarAll = $("button:contains(Unstar all)");
    assert.ok($unstarAll[0].disabled);
});

QUnit.test("auto-focus composer on opening thread", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo User" });
    pyEnv["mail.channel"].create([
        { name: "General" },
        {
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: partnerId }],
            ],
            channel_type: "chat",
        },
    ]);
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, "button:contains(Inbox)");
    assert.hasClass($("button:contains(Inbox)"), "o-active");
    assert.containsOnce($, ".o-DiscussCategoryItem:contains(General)");
    assert.doesNotHaveClass($(".o-DiscussCategoryItem:contains(General)"), "o-active");
    assert.containsOnce($, ".o-DiscussCategoryItem:contains(Demo User)");
    assert.doesNotHaveClass($(".o-DiscussCategoryItem:contains(Demo User)"), "o-active");
    assert.containsNone($, ".o-Composer");

    await click(".o-DiscussCategoryItem:contains(General)");
    assert.hasClass($(".o-DiscussCategoryItem:contains(General)"), "o-active");
    assert.containsOnce($, ".o-Composer");
    assert.strictEqual(document.activeElement, $(".o-Composer-input")[0]);

    await click(".o-DiscussCategoryItem:contains(Demo User)");
    assert.hasClass($(".o-DiscussCategoryItem:contains(Demo User)"), "o-active");
    assert.containsOnce($, ".o-Composer");
    assert.strictEqual(document.activeElement, $(".o-Composer-input")[0]);
});

QUnit.test(
    "receive new chat message: out of odoo focus (notification, channel)",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({ channel_type: "chat" });
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
        const channel = pyEnv["mail.channel"].searchRead([["id", "=", channelId]])[0];
        // simulate receiving a new message with odoo focused
        pyEnv["bus.bus"]._sendone(channel, "mail.channel/new_message", {
            id: channelId,
            message: {
                id: 126,
                model: "mail.channel",
                res_id: channelId,
            },
        });
        await nextTick();
        assert.verifySteps(["set_title_part"]);
    }
);

QUnit.test("receive new chat message: out of odoo focus (notification, chat)", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ channel_type: "chat" });
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
    const channel = pyEnv["mail.channel"].searchRead([["id", "=", channelId]])[0];
    // simulate receiving a new message with odoo focused
    pyEnv["bus.bus"]._sendone(channel, "mail.channel/new_message", {
        id: channelId,
        message: {
            id: 126,
            model: "mail.channel",
            res_id: channelId,
        },
    });
    await nextTick();
    assert.verifySteps(["set_title_part"]);
});

QUnit.test("receive new chat messages: out of odoo focus (tab title)", async (assert) => {
    let step = 0;
    const pyEnv = await startServer();
    const [channelId_1, channelId_2] = pyEnv["mail.channel"].create([
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
    const channel_1 = pyEnv["mail.channel"].searchRead([["id", "=", channelId_1]])[0];
    // simulate receiving a new message in chat 1 with odoo focused
    pyEnv["bus.bus"]._sendone(channel_1, "mail.channel/new_message", {
        id: channelId_1,
        message: {
            id: 126,
            model: "mail.channel",
            res_id: channelId_1,
        },
    });
    await nextTick();
    assert.verifySteps(["set_title_part"]);

    const channel_2 = pyEnv["mail.channel"].searchRead([["id", "=", channelId_2]])[0];
    // simulate receiving a new message in chat 2 with odoo focused
    pyEnv["bus.bus"]._sendone(channel_2, "mail.channel/new_message", {
        id: channelId_2,
        message: {
            id: 127,
            model: "mail.channel",
            res_id: channelId_2,
        },
    });
    await nextTick();
    assert.verifySteps(["set_title_part"]);

    // simulate receiving another new message in chat 2 with odoo focused
    pyEnv["bus.bus"]._sendone(channel_2, "mail.channel/new_message", {
        id: channelId_2,
        message: {
            id: 128,
            model: "mail.channel",
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
    pyEnv["mail.channel"].create({
        channel_member_ids: [
            [0, 0, { is_pinned: false, partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId }],
        ],
        channel_type: "chat",
        uuid: "channel11uuid",
    });
    const { env, openDiscuss } = await start();
    await openDiscuss();
    assert.containsNone($, ".o-DiscussCategoryItem:contains(Demo)");

    // simulate receiving the first message on channel 11
    await afterNextRender(() =>
        env.services.rpc("/mail/chat_post", {
            context: { mockedUserId: userId },
            message_content: "new message",
            uuid: "channel11uuid",
        })
    );
    assert.containsOnce($, ".o-DiscussCategoryItem:contains(Demo)");
});

QUnit.test("'Add Users' button should be displayed in the topbar of channels", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
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
    const channelId = pyEnv["mail.channel"].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId }],
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
    const channelId = pyEnv["mail.channel"].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId }],
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
    "'Hashtag' thread icon is displayed in top bar of channels of type 'channel' limited to a group",
    async (assert) => {
        const pyEnv = await startServer();
        const groupId = pyEnv["res.groups"].create({ name: "testGroup" });
        const channelId = pyEnv["mail.channel"].create({
            channel_type: "channel",
            name: "string",
            group_public_id: groupId,
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.containsOnce($, ".o-Discuss-content .fa-hashtag");
    }
);

QUnit.test(
    "'Globe' thread icon is displayed in top bar of channels of type 'channel' not limited to any group",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({
            channel_type: "channel",
            name: "string",
            group_public_id: false,
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.containsOnce($, ".o-Discuss-content .fa-globe");
    }
);

QUnit.test(
    "Partner IM status is displayed as thread icon in top bar of channels of type 'chat'",
    async (assert) => {
        const pyEnv = await startServer();
        const [partnerId_1, partnerId_2, partnerId_3, partnerId_4] = pyEnv["res.partner"].create([
            { im_status: "online", name: "Michel Online" },
            { im_status: "offline", name: "Jacqueline Offline" },
            { im_status: "away", name: "Nabuchodonosor Away" },
            { im_status: "im_partner", name: "Robert Fired" },
        ]);
        pyEnv["mail.channel"].create([
            {
                channel_member_ids: [
                    [0, 0, { partner_id: pyEnv.currentPartnerId }],
                    [0, 0, { partner_id: partnerId_1 }],
                ],
                channel_type: "chat",
            },
            {
                channel_member_ids: [
                    [0, 0, { partner_id: pyEnv.currentPartnerId }],
                    [0, 0, { partner_id: partnerId_2 }],
                ],
                channel_type: "chat",
            },
            {
                channel_member_ids: [
                    [0, 0, { partner_id: pyEnv.currentPartnerId }],
                    [0, 0, { partner_id: partnerId_3 }],
                ],
                channel_type: "chat",
            },
            {
                channel_member_ids: [
                    [0, 0, { partner_id: pyEnv.currentPartnerId }],
                    [0, 0, { partner_id: partnerId_4 }],
                ],
                channel_type: "chat",
            },
            {
                channel_member_ids: [
                    [0, 0, { partner_id: pyEnv.currentPartnerId }],
                    [0, 0, { partner_id: TEST_USER_IDS.partnerRootId }],
                ],
                channel_type: "chat",
            },
        ]);
        const { openDiscuss } = await start();
        await openDiscuss();
        await click(".o-DiscussCategoryItem:contains('Michel Online')");
        assert.containsOnce($, ".o-Discuss-header .o-ThreadIcon [title='Online']");
        await click(".o-DiscussCategoryItem:contains('Jacqueline Offline')");
        assert.containsOnce($, ".o-Discuss-header .o-ThreadIcon [title='Offline']");
        await click(".o-DiscussCategoryItem:contains('Nabuchodonosor Away')");
        assert.containsOnce($, ".o-Discuss-header .o-ThreadIcon [title='Away']");
        await click(".o-DiscussCategoryItem:contains('Robert Fired')");
        assert.containsOnce($, ".o-Discuss-header .o-ThreadIcon [title='No IM status available']");
        await click(".o-DiscussCategoryItem:contains('OdooBot')");
        assert.containsOnce($, ".o-Discuss-header .o-ThreadIcon [title='Bot']");
    }
);

QUnit.test(
    "'Users' thread icon is displayed in top bar of channels of type 'group'",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({ channel_type: "group" });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.containsOnce($, ".o-Discuss-header .fa-users[title='Grouped Chat']");
    }
);

QUnit.test("Do not trigger chat name server update when it is unchanged", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ channel_type: "chat" });
    const { openDiscuss } = await start({
        mockRPC(route, args, originalRPC) {
            if (args.method === "channel_set_custom_name") {
                assert.step(args.method);
            }
            return originalRPC(route, args);
        },
    });
    await openDiscuss(channelId);
    await editInput(document.body, "input.o-Discuss-threadName", "Mitchell Admin");
    await triggerEvent(document.body, "input.o-Discuss-threadName", "keydown", {
        key: "Enter",
    });
    assert.verifySteps([]);
});

QUnit.test(
    "Do not trigger channel description server update when channel has no description and editing to empty description",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({ name: "General" });
        const { openDiscuss } = await start({
            mockRPC(route, args, originalRPC) {
                if (args.method === "channel_change_description") {
                    assert.step(args.method);
                }
                return originalRPC(route, args);
            },
        });
        await openDiscuss(channelId);
        await editInput(document.body, "input.o-Discuss-threadDescription", "");
        await triggerEvent(document.body, "input.o-Discuss-threadDescription", "keydown", {
            key: "Enter",
        });
        assert.verifySteps([]);
    }
);

QUnit.test("Channel is added to discuss after invitation", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
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
    assert.containsNone($, ".o-DiscussCategoryItem:contains(General)");
    await afterNextRender(() => {
        env.services.orm.call("mail.channel", "add_members", [[channelId]], {
            partner_ids: [pyEnv.currentPartnerId],
            context: { mockedUserId: userId },
        });
    });
    assert.containsOnce($, ".o-DiscussCategoryItem:contains(General)");
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
    await tab1.click(".o-DiscussCategory-chat .o-DiscussCategory-add");
    await tab1.insertText(".o-ChannelSelector input", "Jer");
    await tab1.click(".o-ChannelSelector-suggestion");
    await afterNextRender(() => triggerHotkey("Enter"));
    assert.containsOnce(tab1.target, ".o-DiscussCategoryItem:contains(Jerry Golay)");
    assert.containsOnce(tab2.target, ".o-DiscussCategoryItem:contains(Jerry Golay)");
});

QUnit.test("select another mailbox", async (assert) => {
    patchUiSize({ height: 360, width: 640 });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, ".o-Discuss");
    assert.strictEqual($(".o-Discuss-threadName").val(), "Inbox");
    assert.containsOnce($, "button:contains(Starred)");

    await click("button:contains(Starred)");
    assert.strictEqual($(".o-Discuss-threadName").val(), "Starred");
});

QUnit.test(
    'auto-select "Inbox nav bar" when discuss had inbox as active thread',
    async (assert) => {
        patchUiSize({ height: 360, width: 640 });
        const { openDiscuss } = await start();
        await openDiscuss();
        assert.strictEqual($(".o-Discuss-threadName").val(), "Inbox");
        assert.containsOnce($, ".o-MessagingMenu-navbar:contains(Mailboxes) .fw-bolder");
        assert.containsOnce($, "button:contains(Inbox).o-active");
        assert.containsOnce($, "h4:contains(Congratulations, your inbox is empty)");
    }
);

QUnit.test(
    "composer should be focused automatically after clicking on the send button [REQUIRE FOCUS]",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({ name: "test" });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        await insertText(".o-Composer-input", "Dummy Message");
        await click(".o-Composer-send");
        assert.strictEqual(document.activeElement, $(".o-Composer-input")[0]);
    }
);

QUnit.test(
    "mark channel as seen if last message is visible when switching channels when the previous channel had a more recent last message than the current channel [REQUIRE FOCUS]",
    async (assert) => {
        const pyEnv = await startServer();
        const [channelId_1, channelId_2] = pyEnv["mail.channel"].create([
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
                model: "mail.channel",
                res_id: channelId_1,
            },
            {
                body: "newest message",
                model: "mail.channel",
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
        const channelId = pyEnv["mail.channel"].create({ name: "test" });
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
            editInput(document.body, ".o-Composer input[type=file]", [file])
        );
        assert.containsOnce($, ".o-AttachmentCard");
        assert.containsOnce($, ".o-AttachmentCard.o-isUploading");
        assert.containsOnce($, ".o-Composer-send");

        // Try to send message
        triggerHotkey("Enter");
        assert.verifySteps(["notification"]);
    }
);

QUnit.test("new messages separator [REQUIRE FOCUS]", async (assert) => {
    // this test requires several messages so that the last message is not
    // visible. This is necessary in order to display 'new messages' and not
    // remove from DOM right away from seeing last message.
    // AKU TODO: thread specific test
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Foreigner partner" });
    const userId = pyEnv["res.users"].create({
        name: "Foreigner user",
        partner_id: partnerId,
    });
    const channelId = pyEnv["mail.channel"].create({ name: "test", uuid: "randomuuid" });
    let lastMessageId;
    for (let i = 1; i <= 25; i++) {
        lastMessageId = pyEnv["mail.message"].create({
            body: "not empty",
            model: "mail.channel",
            res_id: channelId,
        });
    }
    const [memberId] = pyEnv["mail.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", pyEnv.currentPartnerId],
    ]);
    pyEnv["mail.channel.member"].write([memberId], { seen_message_id: lastMessageId });
    const { env, openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsN($, ".o-Message", 25);
    assert.containsNone($, "hr + span:contains(New messages)");

    $(".o-Discuss-content .o-Thread")[0].scrollTop = 0;
    // composer is focused by default, we remove that focus
    $(".o-Composer-input")[0].blur();
    // simulate receiving a message
    await afterNextRender(async () =>
        env.services.rpc("/mail/chat_post", {
            context: { mockedUserId: userId },
            message_content: "hu",
            uuid: "randomuuid",
        })
    );
    assert.containsN($, ".o-Message", 26);
    assert.containsOnce($, "hr + span:contains(New messages)");
    const messageList = $(".o-Discuss-content .o-Thread")[0];
    messageList.scrollTop = messageList.scrollHeight - messageList.clientHeight;
    assert.containsOnce($, "hr + span:contains(New messages)");

    await afterNextRender(() => $(".o-Composer-input")[0].focus());
    assert.containsNone($, "hr + span:contains(New messages)");
});

QUnit.test("failure on loading messages should display error", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        channel_type: "channel",
        name: "General",
    });
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === "/mail/channel/messages") {
                return Promise.reject();
            }
        },
    });
    await openDiscuss(channelId, { waitUntilMessagesLoaded: false });
    assert.containsOnce($, ".o-Thread-error:contains(An error occurred while fetching messages.)");
});

QUnit.test("failure on loading messages should prompt retry button", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        channel_type: "channel",
        name: "General",
    });
    const { openDiscuss } = await start({
        async mockRPC(route, args) {
            if (route === "/mail/channel/messages") {
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
        const channelId = pyEnv["mail.channel"].create({
            channel_type: "channel",
            name: "General",
        });
        pyEnv["mail.message"].create(
            [...Array(60).keys()].map(() => {
                return {
                    body: "coucou",
                    model: "mail.channel",
                    res_id: channelId,
                };
            })
        );
        const { openDiscuss } = await start({
            async mockRPC(route, args) {
                if (route === "/mail/channel/messages" && messageFetchShouldFail) {
                    return Promise.reject();
                }
            },
        });
        await openDiscuss(channelId);
        messageFetchShouldFail = true;
        await click("button:contains(Load More)");
        assert.containsN($, ".o-Message", 30);
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
        const channelId = pyEnv["mail.channel"].create({
            channel_type: "channel",
            name: "General",
        });
        pyEnv["mail.message"].create(
            [...Array(60).keys()].map(() => {
                return {
                    body: "coucou",
                    model: "mail.channel",
                    res_id: channelId,
                };
            })
        );
        const { openDiscuss } = await start({
            async mockRPC(route, args) {
                if (route === "/mail/channel/messages" && messageFetchShouldFail) {
                    return Promise.reject();
                }
            },
        });
        await openDiscuss(channelId);
        messageFetchShouldFail = true;
        await click("button:contains(Load More)");
        assert.containsOnce(
            $,
            ".o-Thread-error:contains(An error occurred while fetching messages.)"
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
        const channelId = pyEnv["mail.channel"].create({
            channel_type: "channel",
            name: "General",
        });
        pyEnv["mail.message"].create(
            [...Array(90).keys()].map(() => {
                return {
                    body: "coucou",
                    model: "mail.channel",
                    res_id: channelId,
                };
            })
        );
        const { openDiscuss } = await start({
            async mockRPC(route, args) {
                if (route === "/mail/channel/messages") {
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
        assert.containsN($, ".o-Message", 60);
    }
);

QUnit.test("composer state: attachments save and restore", async (assert) => {
    const pyEnv = await startServer();
    const [channelId] = pyEnv["mail.channel"].create([{ name: "General" }, { name: "Special" }]);
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    // Add attachment in a message for #general
    await afterNextRender(async () => {
        const file = await createFile({
            content: "hello, world",
            contentType: "text/plain",
            name: "text.txt",
        });
        editInput(document.body, ".o-Composer input[type=file]", [file]);
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
    await afterNextRender(() => editInput(document.body, ".o-Composer input[type=file]", files));
    // Switch back to #general
    await click("button:contains(General)");
    // Check attachment is reloaded
    assert.containsOnce($, ".o-Composer .o-AttachmentCard");
    assert.containsOnce($, ".o-AttachmentCard:contains(text.txt)");

    // Switch back to #special
    await click("button:contains(Special)");
    assert.containsN($, ".o-Composer .o-AttachmentCard", 3);
    assert.containsOnce($, ".o-AttachmentCard:contains(text2.txt)");
    assert.containsOnce($, ".o-AttachmentCard:contains(text3.txt)");
    assert.containsOnce($, ".o-AttachmentCard:contains(text4.txt)");
});

QUnit.test(
    "sidebar: cannot unpin channel group_based_subscription: mandatorily pinned",
    async (assert) => {
        const pyEnv = await startServer();
        pyEnv["mail.channel"].create({
            name: "General",
            channel_member_ids: [[0, 0, { is_pinned: false, partner_id: pyEnv.currentPartnerId }]],
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
    const [channelId_1, channelId_2] = pyEnv["mail.channel"].create([
        { name: "Channel1" },
        { name: "Channel2" },
    ]);
    for (let i = 1; i <= 25; i++) {
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "mail.channel",
            res_id: channelId_1,
        });
    }
    for (let i = 1; i <= 24; i++) {
        pyEnv["mail.message"].create({
            body: "not empty",
            model: "mail.channel",
            res_id: channelId_2,
        });
    }
    const { openDiscuss } = await start();
    await openDiscuss(channelId_1);
    assert.containsN($, ".o-Message", 25);
    let thread = $(".o-Thread")[0];
    assert.ok(isScrolledToBottom(thread));

    $(".o-Thread")[0].scrollTop = 0;
    assert.strictEqual($(".o-Thread")[0].scrollTop, 0);

    // Ensure scrollIntoView of channel 2 has enough time to complete before
    // going back to channel 1. Await is needed to prevent the scrollIntoView
    // initially planned for channel 2 to actually apply on channel 1.
    // task-2333535
    await click("button:contains(Channel2)");
    assert.containsN($, ".o-Message", 24);

    await click("button:contains(Channel1)");
    assert.strictEqual($(".o-Thread")[0].scrollTop, 0);

    await click("button:contains(Channel2)");
    thread = $(".o-Thread")[0];
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
    const channelId = pyEnv["mail.channel"].create({
        channel_member_ids: [
            [
                0,
                0,
                {
                    is_pinned: true,
                    partner_id: pyEnv.currentPartnerId,
                },
            ],
            [0, 0, { partner_id: correspondentPartnerId }],
        ],
        channel_type: "chat",
    });
    await env.services.rpc("/mail/channel/notify_typing", {
        context: { mockedPartnerId: correspondentPartnerId },
        is_typing: true,
        channel_id: channelId,
    });
    const [channel] = pyEnv["mail.channel"].searchRead([["id", "=", channelId]]);
    await afterNextRender(
        async () =>
            await env.services.rpc("/mail/chat_post", {
                context: { mockedUserId: correspondentUserId },
                message_content: "hello world",
                uuid: channel.uuid,
            })
    );
    await click(".o-DiscussCategory-chat + .o-DiscussCategoryItem:contains(Albert)");
    assert.containsOnce($, ".o-Message:contains(hello world)");
});

QUnit.test("Create a direct message channel when clicking on start a meeting", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        channel_type: "channel",
        name: "General",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("button:contains(Start a meeting)");
    assert.containsOnce($, "button:contains(Mitchell Admin)");
    assert.containsOnce($, ".o-Call");
});

QUnit.test("Member list and settings menu are exclusive", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("button[title='Show Member List']");
    assert.containsOnce($, ".o-ChannelMemberList");
    await click("button[title='Show Call Settings']");
    assert.containsOnce($, ".o-CallSettings");
    assert.containsNone($, ".o-ChannelMemberList");
});
