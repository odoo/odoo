import {
    assertSteps,
    click,
    contains,
    defineMailModels,
    insertText,
    onRpcBefore,
    openDiscuss,
    start,
    startServer,
    step,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { Command, onRpc, serverState } from "@web/../tests/web_test_helpers";

import { pick } from "@web/core/utils/objects";

describe.current.tags("desktop");
defineMailModels();

test("can create a new channel [REQUIRE FOCUS]", async () => {
    const pyEnv = await startServer();
    onRpcBefore((route, args) => {
        if (route.startsWith("/mail") || route.startsWith("/discuss/channel/messages")) {
            step(`${route} - ${JSON.stringify(args)}`);
        }
    });
    onRpc((params) => {
        if (
            params.model === "discuss.channel" &&
            ["search_read", "channel_create"].includes(params.method)
        ) {
            step(
                `${params.route} - ${JSON.stringify(
                    pick(params, "args", "kwargs", "method", "model")
                )}`
            );
        }
    });
    await start();
    await assertSteps([
        `/mail/action - ${JSON.stringify({
            init_messaging: {},
            failures: true,
            systray_get_activities: true,
            context: { lang: "en", tz: "taht", uid: serverState.userId, allowed_company_ids: [1] },
        })}`,
    ]);
    await openDiscuss();
    await assertSteps([
        `/mail/data - ${JSON.stringify({
            channels_as_member: true,
            context: { lang: "en", tz: "taht", uid: serverState.userId, allowed_company_ids: [1] },
        })}`,
        '/mail/inbox/messages - {"limit":30}',
    ]);
    await click(".o-mail-DiscussSidebar [title='Add or join a channel']");
    await contains(".o-mail-DiscussSidebarChannel", { count: 0 });
    await insertText(".o-discuss-ChannelSelector input", "abc");
    await assertSteps([
        `/web/dataset/call_kw/discuss.channel/search_read - ${JSON.stringify({
            args: [],
            kwargs: {
                limit: 10,
                domain: [
                    ["parent_channel_id", "=", false],
                    ["channel_type", "=", "channel"],
                    ["name", "ilike", "abc"],
                ],
                fields: ["name"],
                context: {
                    lang: "en",
                    tz: "taht",
                    uid: serverState.userId,
                    allowed_company_ids: [1],
                },
            },
            method: "search_read",
            model: "discuss.channel",
        })}`,
    ]);
    await click(".o-discuss-ChannelSelector-suggestion");
    await contains(".o-mail-DiscussSidebarChannel");
    await contains(".o-mail-Discuss-content .o-mail-Message", { count: 0 });
    const [channelId] = pyEnv["discuss.channel"].search([["name", "=", "abc"]]);
    const [selfMember] = pyEnv["discuss.channel.member"].search_read([
        ["channel_id", "=", channelId],
        ["partner_id", "=", serverState.partnerId],
    ]);
    await assertSteps([
        `/web/dataset/call_kw/discuss.channel/channel_create - ${JSON.stringify({
            args: ["abc", null],
            kwargs: {
                context: {
                    lang: "en",
                    tz: "taht",
                    uid: serverState.userId,
                    allowed_company_ids: [1],
                },
            },
            method: "channel_create",
            model: "discuss.channel",
        })}`,
        `/discuss/channel/messages - {"channel_id":${channelId},"limit":60,"around":${selfMember.new_message_separator}}`,
    ]);
});

test("do not close channel selector when creating chat conversation after selection", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Mario" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    await start();
    await openDiscuss();
    await click("[title='Start a conversation']");
    await insertText(".o-discuss-ChannelSelector input", "mario");
    await click(".o-discuss-ChannelSelector-suggestion");
    await contains(".o-discuss-ChannelSelector span[title='Mario']");
    await contains(".o-mail-DiscussSidebarChannel", { count: 0 });
    triggerHotkey("Backspace");
    await contains(".o-discuss-ChannelSelector span[title='Mario']", { count: 0 });
    await insertText(".o-discuss-ChannelSelector input", "mario");
    await contains(".o-discuss-ChannelSelector-suggestion");
    triggerHotkey("Enter");
    await contains(".o-discuss-ChannelSelector span[title='Mario']");
    await contains(".o-mail-DiscussSidebarChannel", { count: 0 });
});

test("can join a chat conversation", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Mario" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    onRpcBefore((route, args) => {
        if (route.startsWith("/mail") || route.startsWith("/discuss")) {
            step(`${route} - ${JSON.stringify(args)}`);
        }
    });
    onRpc((params) => {
        if (
            params.model === "discuss.channel" &&
            ["search_read", "channel_create", "channel_get"].includes(params.method)
        ) {
            step(
                `${params.route} - ${JSON.stringify(
                    pick(params, "args", "kwargs", "method", "model")
                )}`
            );
        }
    });
    await start();
    await assertSteps([
        `/mail/action - ${JSON.stringify({
            init_messaging: {},
            failures: true,
            systray_get_activities: true,
            context: { lang: "en", tz: "taht", uid: serverState.userId, allowed_company_ids: [1] },
        })}`,
    ]);
    await openDiscuss();
    await assertSteps([
        `/mail/data - ${JSON.stringify({
            channels_as_member: true,
            context: { lang: "en", tz: "taht", uid: serverState.userId, allowed_company_ids: [1] },
        })}`,
        '/mail/inbox/messages - {"limit":30}',
    ]);
    await click(".o-mail-DiscussSidebar [title='Start a conversation']");
    await contains(".o-mail-DiscussSidebarChannel", { count: 0 });
    await insertText(".o-discuss-ChannelSelector input", "mario");
    await click(".o-discuss-ChannelSelector-suggestion");
    await contains(".o-discuss-ChannelSelector-suggestion", { count: 0 });
    triggerHotkey("Enter");
    await contains(".o-mail-DiscussSidebarChannel");
    await contains(".o-mail-Message", { count: 0 });
    const channelId = pyEnv["discuss.channel"].search([["name", "=", "Mario, Mitchell Admin"]]);
    await assertSteps([
        `/web/dataset/call_kw/discuss.channel/channel_get - ${JSON.stringify({
            args: [],
            kwargs: {
                partners_to: [partnerId],
                force_open: true,
                context: {
                    lang: "en",
                    tz: "taht",
                    uid: serverState.userId,
                    allowed_company_ids: [1],
                },
            },
            method: "channel_get",
            model: "discuss.channel",
        })}`,
        `/discuss/channel/messages - {"channel_id":${channelId},"limit":60,"around":0}`,
    ]);
});

test("can create a group chat conversation", async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { name: "Mario" },
        { name: "Luigi" },
    ]);
    pyEnv["res.users"].create([{ partner_id: partnerId_1 }, { partner_id: partnerId_2 }]);
    await start();
    await openDiscuss();
    await click(".o-mail-DiscussSidebar [title='Start a conversation']");
    await contains(".o-mail-DiscussSidebarChannel", { count: 0 });
    await insertText(".o-discuss-ChannelSelector input", "Mario");
    await click(".o-discuss-ChannelSelector-suggestion");
    await contains(".o-discuss-ChannelSelector-suggestion", { count: 0 });
    await insertText(".o-discuss-ChannelSelector input", "Luigi");
    await click(".o-discuss-ChannelSelector-suggestion");
    await contains(".o-discuss-ChannelSelector-suggestion", { count: 0 });
    triggerHotkey("Enter");
    await contains(".o-mail-DiscussSidebarChannel");
    await contains(".o-mail-Message", { count: 0 });
});

test("should create DM chat when adding self and another user", async () => {
    const pyEnv = await startServer();
    const partner_id = pyEnv["res.partner"].create({ name: "Mario", im_status: "online" });
    pyEnv["res.users"].create({ partner_id });
    await start();
    await openDiscuss();
    await click(".o-mail-DiscussSidebar [title='Start a conversation']");
    await contains(".o-mail-DiscussSidebarChannel", { count: 0 });
    await insertText(".o-discuss-ChannelSelector input", "Mi"); // Mitchell Admin
    await click(".o-discuss-ChannelSelector-suggestion");
    await contains(".o-discuss-ChannelSelector-suggestion", { count: 0 });
    await insertText(".o-discuss-ChannelSelector input", "Mario");
    await click(".o-discuss-ChannelSelector-suggestion");
    await contains(".o-discuss-ChannelSelector-suggestion", { count: 0 });
    triggerHotkey("Enter");
    await contains(".o-mail-DiscussSidebarChannel", { text: "Mario" });
});

test("chat search should display no result when no matches found", async () => {
    await start();
    await openDiscuss();
    await click(".o-mail-DiscussSidebar [title='Start a conversation']");
    await insertText(".o-discuss-ChannelSelector input", "Rainbow Panda");
    await contains(".o-discuss-ChannelSelector-suggestion", { text: "No results found" });
});

test("chat search should not be visible when clicking outside of the field", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Panda" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    await start();
    await openDiscuss();
    await click(".o-mail-DiscussSidebar [title='Start a conversation']");
    await insertText(".o-discuss-ChannelSelector input", "Panda");
    await contains(".o-discuss-ChannelSelector-suggestion");
    await click(".o-mail-DiscussSidebar");
    await contains(".o-discuss-ChannelSelector-suggestion", { count: 0 });
});

test("sidebar: add channel", async () => {
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory-channel .o-mail-DiscussSidebarCategory-add");
    expect(
        $(".o-mail-DiscussSidebarCategory-channel .o-mail-DiscussSidebarCategory-add")[0]
    ).toHaveAttribute("title", "Add or join a channel");
    await click(".o-mail-DiscussSidebarCategory-channel .o-mail-DiscussSidebarCategory-add");
    await contains(".o-discuss-ChannelSelector");
    await contains(".o-discuss-ChannelSelector input[placeholder='Add or join a channel']");
});

test("Chat is added to discuss on other tab that the one that joined", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Jerry Golay" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const env1 = await start({ asTab: true });
    const env2 = await start({ asTab: true });
    await openDiscuss(undefined, { target: env1 });
    await openDiscuss(undefined, { target: env2 });
    await click(".o-mail-DiscussSidebarCategory-chat .o-mail-DiscussSidebarCategory-add", {
        target: env1,
    });
    await insertText(".o-discuss-ChannelSelector input", "Jer", { target: env1 });
    await click(".o-discuss-ChannelSelector-suggestion", { target: env1 });
    triggerHotkey("Enter");
    await contains(".o-mail-DiscussSidebarChannel", { target: env1, text: "Jerry Golay" });
    await contains(".o-mail-DiscussSidebarChannel", { target: env2, text: "Jerry Golay" });
});

test("no conversation selected when opening non-existing channel in discuss", async () => {
    await startServer();
    await start();
    await openDiscuss(200); // non-existing id
    await contains("h4", { text: "No conversation selected." });
    await contains(".o-mail-DiscussSidebarCategory-channel .oi-chevron-down");
    await click(".o-mail-DiscussSidebar .btn", { text: "Channels" }); // check no crash
    await contains(".o-mail-DiscussSidebarCategory-channel .oi-chevron-right");
});

test("can access portal partner profile from avatar popover", async () => {
    const pyEnv = await startServer();
    const joelPartnerId = pyEnv["res.partner"].create({
        name: "Joel",
        user_ids: [Command.create({ name: "Joel", share: true })],
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: joelPartnerId }),
        ],
    });
    pyEnv["mail.message"].create({
        author_id: joelPartnerId,
        body: "Hello!",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message-avatar", {
        parent: [".o-mail-Message", { text: "Joel" }],
    });
    await click("button", { text: "View Profile" });
    await contains(".o_form_view");
    await contains(".o_field_widget[name='name'] .o_input", { value: "Joel" });
});

test("Preserve letter case and accents when creating channel from sidebar", async () => {
    await start();
    await openDiscuss();
    await click(".o-mail-DiscussSidebar [title='Add or join a channel']");
    await insertText(".o-discuss-ChannelSelector input", "Crème brûlée Fan Club");
    await click(".o-discuss-ChannelSelector-suggestion");
    await contains(".o-mail-Discuss-threadName", { value: "Crème brûlée Fan Club" });
});
