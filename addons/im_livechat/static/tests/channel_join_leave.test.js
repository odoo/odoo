import { Command, onRpc, serverState } from "@web/../tests/web_test_helpers";
import { defineLivechatModels } from "@im_livechat/../tests/livechat_test_helpers";
import {
    click,
    contains,
    openDiscuss,
    setupChatHub,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { waitFor, waitForNone } from "@odoo/hoot-dom";
import { withGuest } from "@mail/../tests/mock_server/mail_mock_server";
import { rpc } from "@web/core/network/rpc";
import { livechatLastAgentLeaveFromChatWindow } from "./im_livechat_shared_tests";

describe.current.tags("desktop");
defineLivechatModels();

test("from the command palette", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write([serverState.userId], {
        group_ids: pyEnv["res.groups"]
            .search_read([["id", "=", serverState.groupLivechatId]])
            .map(({ id }) => id),
    });
    pyEnv["im_livechat.channel"].create({ name: "HR", user_ids: [serverState.userId] });
    await start();
    await triggerHotkey("control+k");
    await click(".o_command", { text: "Leave HR" });
    await contains(".o_notification", { text: "You left HR." });
    await contains(".o_command", { text: "HR", count: 0 });
    await triggerHotkey("control+k");
    await click(".o_command", { text: "Join HR" });
    await contains(".o_notification", { text: "You joined HR." });
});

test("from chat window", livechatLastAgentLeaveFromChatWindow);

test("visitor leaving ends the livechat conversation", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write([serverState.userId], {
        group_ids: pyEnv["res.groups"]
            .search_read([["id", "=", serverState.groupLivechatId]])
            .map(({ id }) => id),
    });
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor" });
    const livechatChannelId = pyEnv["im_livechat.channel"].create({
        name: "HR",
        user_ids: [serverState.userId],
    });
    const channel_id = pyEnv["discuss.channel"].create({
        channel_type: "livechat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        livechat_channel_id: livechatChannelId,
        create_uid: serverState.publicUserId,
    });
    setupChatHub({ opened: [channel_id] });
    await start();
    await waitFor(".o-mail-ChatWindow:count(1)");
    // simulate visitor leaving
    await withGuest(guestId, () => rpc("/im_livechat/visitor_leave_session", { channel_id }));
    await contains("span", { text: "This live chat conversation has ended." });
    await click("button[title*='Close Chat Window']");
    await waitForNone(".o-mail-ChatWindow");
});

test("ended livechat hides join channel action", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write([serverState.userId], {
        group_ids: pyEnv["res.groups"]
            .search_read([["id", "=", serverState.groupLivechatId]])
            .map(({ id }) => id),
    });
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "livechat",
        channel_member_ids: [
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        create_uid: serverState.publicUserId,
    });
    await start();
    await openDiscuss(channelId);
    await waitFor("button[name='join-channel']:count(1)");
    await withGuest(guestId, () =>
        rpc("/im_livechat/visitor_leave_session", { channel_id: channelId })
    );
    await waitForNone("button[name='join-channel']");
});

test("leaving chat window triggers a single RPC", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor #1" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "livechat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
    });
    pyEnv["mail.message"].create({
        body: "Last message from Visitor #1",
        model: "discuss.channel",
        res_id: channelId,
    });
    setupChatHub({ opened: [channelId] });
    onRpc("discuss.channel", "action_unfollow", () => expect.step("action_unfollow"));
    await start();
    await waitFor(".o-mail-ChatWindow:count(1)");
    await waitFor(".o-mail-Message:contains('Last message from Visitor #1'):count(1)");
    await click("[title='Open Actions Menu']", {
        parent: [".o-mail-ChatWindow:contains('Visitor #1')"],
    });
    await click(".o-dropdown-item:text('Close Conversation')");
    await waitFor(
        ".modal-header:contains('Closing this will end the live chat with Visitor #1. Are you sure you want to proceed?'):count(1)"
    );
    await click("button:contains(Close Conversation)");
    await waitForNone(".o-mail-ChatWindow");
    await expect.waitForSteps(["action_unfollow"]);
});
