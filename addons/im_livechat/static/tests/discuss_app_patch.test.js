import {
    click,
    contains,
    insertText,
    openDiscuss,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { withGuest } from "@mail/../tests/mock_server/mail_mock_server";
import { describe, mockDate, test } from "@odoo/hoot";
import { Command, serverState } from "@web/../tests/web_test_helpers";

import { rpc } from "@web/core/network/rpc";
import { defineLivechatModels } from "./livechat_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test("add livechat in the sidebar on visitor sending first message", async () => {
    mockDate("2023-01-03 12:00:00"); // so that it's after last interest (mock server is in 2019 by default!)
    const pyEnv = await startServer();
    pyEnv["res.users"].write([serverState.userId], { im_status: "online" });
    const countryId = pyEnv["res.country"].create({ code: "be", name: "Belgium" });
    const livechatChannelId = pyEnv["im_livechat.channel"].create({
        user_ids: [serverState.userId],
    });
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                unpin_dt: "2021-01-01 12:00:00",
                last_interest_dt: "2021-01-01 10:00:00",
                livechat_member_type: "agent",
                partner_id: serverState.partnerId,
            }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        channel_type: "livechat",
        country_id: countryId,
        livechat_channel_id: livechatChannelId,
    });
    await start();
    await openDiscuss("tab:livechat");
    await contains(".o-mail-MessagingMenuEmpty:has(:text('No Livechat Session!'))");
    // simulate livechat visitor sending a message
    withGuest(guestId, () =>
        rpc("/mail/message/post", {
            post_data: {
                body: "Hello, I need help!",
                message_type: "comment",
                subtype_xmlid: "mail.mt_comment",
            },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-MessagingMenuItem:has(:text(Visitor))");
});

test("invite button should be present on livechat", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        channel_type: "livechat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-livechat-ChannelInfoList"); // wait for auto-open of this panel
    await click("button[title='Members']");
    await contains("button[title='Add People']");
});

test("command palette search finds livechats", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        channel_type: "livechat",
    });
    await start();
    await triggerHotkey("control+k");
    await insertText(".o_command_palette_search input", "@");
    await click("a", { text: "Visitor 11" });
    await contains(".o-mail-ChatWindow-displayName:text('Visitor 11')");
});

test("open visitor's partner profile if visitor has one", async () => {
    const pyEnv = await startServer();
    const livechatPartner = pyEnv["res.partner"].create({ name: "Joel Willis" });
    const channel = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ partner_id: livechatPartner, livechat_member_type: "visitor" }),
        ],
        channel_type: "livechat",
    });
    await start();
    await openDiscuss(channel);
    await click("a[title='View Contact']");
    await contains("div.o_field_widget input:value(Joel Willis)");
});

test("Conversation description works in livechat", async () => {
    const pyEnv = await startServer();
    const livechatPartner = pyEnv["res.partner"].create({ name: "Joel Willis" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ partner_id: livechatPartner, livechat_member_type: "visitor" }),
        ],
        channel_type: "livechat",
        description: "Yup, that customer again...",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-input:focus");
    await contains(
        "input.o-mail-DiscussContent-threadDescription:value(Yup, that customer again...)"
    );
});

test("reply to message composer should disappear when livechat conversation ends", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        channel_type: "livechat",
    });
    pyEnv["mail.message"].create({
        author_guest_id: guestId,
        body: "Hello, I need help!",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message:has(:text('Hello, I need help!')) [title='Expand']");
    await click(".o-dropdown-item:text('Reply')");
    await contains(".o-mail-Composer:has(:text('Replying to Visitor'))");
    await withGuest(guestId, () =>
        rpc("/im_livechat/visitor_leave_session", { channel_id: channelId })
    );
    await contains("span:text('This live chat conversation has ended.')");
    await contains(".o-mail-Composer", { count: 0 });
});
