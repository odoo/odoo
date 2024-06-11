/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { click, contains, insertText } from "@web/../tests/utils";

import { Command } from "@mail/../tests/helpers/command";
import { start } from "@mail/../tests/helpers/test_utils";

QUnit.module("discuss (patch)");

QUnit.test("add livechat in the sidebar on visitor sending first message", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write([pyEnv.currentUserId], { im_status: "online" });
    const countryId = pyEnv["res.country"].create({ code: "be", name: "Belgium" });
    const livechatChannelId = pyEnv["im_livechat.channel"].create({
        user_ids: [pyEnv.currentUserId],
    });
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor (Belgium)" });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor (Belgium)",
        channel_member_ids: [
            [0, 0, { is_pinned: false, partner_id: pyEnv.currentPartnerId }],
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        country_id: countryId,
        livechat_channel_id: livechatChannelId,
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    const { env, openDiscuss } = await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebar");
    await contains(".o-mail-DiscussSidebarCategory-livechat", { count: 0 });
    // simulate livechat visitor sending a message
    const [channel] = pyEnv["discuss.channel"].searchRead([["id", "=", channelId]]);
    pyEnv.withGuest(guestId, () =>
        env.services.rpc("/im_livechat/chat_post", {
            uuid: channel.uuid,
            message_content: "new message",
        })
    );
    await contains(".o-mail-DiscussSidebarCategory-livechat + .o-mail-DiscussSidebarChannel", {
        text: "Visitor (Belgium)",
    });
});

QUnit.test("invite button should be present on livechat", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 11",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Discuss button[title='Add Users']");
});

QUnit.test(
    "livechats are sorted by last activity time in the sidebar: most recent at the top",
    async () => {
        const pyEnv = await startServer();
        const guestId_1 = pyEnv["mail.guest"].create({ name: "Visitor 11" });
        const guestId_2 = pyEnv["mail.guest"].create({ name: "Visitor 12" });
        pyEnv["discuss.channel"].create([
            {
                anonymous_name: "Visitor 11",
                channel_member_ids: [
                    [
                        0,
                        0,
                        {
                            last_interest_dt: "2021-01-01 10:00:00",
                            partner_id: pyEnv.currentPartnerId,
                        },
                    ],
                    Command.create({ guest_id: guestId_1 }),
                ],
                channel_type: "livechat",
                livechat_operator_id: pyEnv.currentPartnerId,
            },
            {
                anonymous_name: "Visitor 12",
                channel_member_ids: [
                    [
                        0,
                        0,
                        {
                            last_interest_dt: "2021-02-01 10:00:00",
                            partner_id: pyEnv.currentPartnerId,
                        },
                    ],
                    Command.create({ guest_id: guestId_2 }),
                ],
                channel_type: "livechat",
                livechat_operator_id: pyEnv.currentPartnerId,
            },
        ]);
        const { openDiscuss } = await start();
        await openDiscuss();
        await contains(".o-mail-DiscussSidebarChannel", { count: 2 });
        await contains(":nth-child(1 of .o-mail-DiscussSidebarChannel)", { text: "Visitor 12" });
        await click(":nth-child(2 of .o-mail-DiscussSidebarChannel)", { text: "Visitor 11" });
        await insertText(".o-mail-Composer-input", "Blabla");
        await click(".o-mail-Composer-send:enabled");
        await contains(":nth-child(1 of .o-mail-DiscussSidebarChannel)", { text: "Visitor 11" });
        await contains(":nth-child(2 of .o-mail-DiscussSidebarChannel)", { text: "Visitor 12" });
    }
);
