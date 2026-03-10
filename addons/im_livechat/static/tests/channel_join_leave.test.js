import { Command, serverState } from "@web/../tests/web_test_helpers";
import { defineLivechatModels } from "@im_livechat/../tests/livechat_test_helpers";
import {
    click,
    contains,
    listenStoreFetch,
    setupChatHub,
    start,
    startServer,
    triggerHotkey,
    waitStoreFetch,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
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
    listenStoreFetch("channels_as_member");
    setupChatHub({ opened: [channel_id] });
    await start();
    await contains(".o-mail-ChatWindow");
    // The first message received will trigger the fetch of
    // `channels_as_member` which can conflict with the rest of the
    // test. Open the messaging menu to do it beforehand.
    await click(".o_menu_systray i[aria-label='Messages']");
    await waitStoreFetch("channels_as_member");
    // simulate visitor leaving
    await withGuest(guestId, () => rpc("/im_livechat/visitor_leave_session", { channel_id }));
    await contains("span", { text: "This live chat conversation has ended" });
    await click("button[title*='Close Chat Window']");
    await contains(".o-mail-ChatWindow", { count: 0 });
});
