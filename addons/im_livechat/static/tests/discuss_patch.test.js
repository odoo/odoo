import {
    click,
    contains,
    insertText,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { withGuest } from "@mail/../tests/mock_server/mail_mock_server";
import { describe, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { Command, serverState } from "@web/../tests/web_test_helpers";

import { rpc } from "@web/core/network/rpc";
import { defineLivechatModels } from "./livechat_test_helpers";
import { press } from "@odoo/hoot-dom";

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
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebar");
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
    await contains(
        ".o-mail-DiscussSidebarCategory-livechat + .o-mail-DiscussSidebarChannel-container",
        {
            text: "Visitor (Belgium)",
        }
    );
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
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Discuss button[title='Invite People']");
});

test("livechats are sorted by last activity time in the sidebar: most recent at the top", async () => {
    mockDate("2023-01-03 12:00:00"); // so that it's after last interest (mock server is in 2019 by default!)
    const pyEnv = await startServer();
    const guestId_1 = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    const guestId_2 = pyEnv["mail.guest"].create({ name: "Visitor 12" });
    pyEnv["discuss.channel"].create([
        {
            channel_member_ids: [
                Command.create({
                    last_interest_dt: "2021-01-01 10:00:00",
                    livechat_member_type: "agent",
                    partner_id: serverState.partnerId,
                }),
                Command.create({ guest_id: guestId_1, livechat_member_type: "visitor" }),
            ],
            channel_type: "livechat",
            livechat_operator_id: serverState.partnerId,
        },
        {
            channel_member_ids: [
                Command.create({
                    last_interest_dt: "2021-02-01 10:00:00",
                    livechat_member_type: "agent",
                    partner_id: serverState.partnerId,
                }),
                Command.create({ guest_id: guestId_2, livechat_member_type: "visitor" }),
            ],
            channel_type: "livechat",
            livechat_operator_id: serverState.partnerId,
        },
    ]);
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel", { count: 2 });
    await contains(":nth-child(1 of .o-mail-DiscussSidebarChannel-container)", {
        text: "Visitor 12",
    });
    await click(".o-mail-DiscussSidebarChannel", { text: "Visitor 11" });
    await insertText(".o-mail-Composer-input", "Blabla");
    await press("Enter");
    await contains(":nth-child(1 of .o-mail-DiscussSidebarChannel-container)", {
        text: "Visitor 11",
    });
    await contains(":nth-child(2 of .o-mail-DiscussSidebarChannel-container)", {
        text: "Visitor 12",
    });
});

test("sidebar search finds livechats", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss();
    await click("input[placeholder='Search conversations']");
    await click("a", { text: "Visitor 11" });
    await contains(".o-mail-Discuss-threadName[title='Visitor 11']");
});

test("open visitor's partner profile if visitor has one", async () => {
    const pyEnv = await startServer();
    const livechatPartner = pyEnv["res.partner"].create({ name: "Joel Willis" });
    const channel = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: livechatPartner }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss(channel);
    await click("a[title='View Contact']");
    await contains("div.o_field_widget > input:value(Joel Willis)");
});
