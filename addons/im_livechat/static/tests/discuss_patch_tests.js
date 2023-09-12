/* @odoo-module */

import { click, contains, insertText } from "@bus/../tests/helpers/test_utils";

import { Command } from "@mail/../tests/helpers/command";
import { start, startServer } from "@mail/../tests/helpers/test_utils";

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
    await contains(".o-mail-DiscussSidebarCategory-livechat");
    await contains(".o-mail-DiscussSidebarCategory-livechat + .o-mail-DiscussSidebarChannel");
    await contains(
        ".o-mail-DiscussSidebarCategory-livechat + .o-mail-DiscussSidebarChannel:contains(Visitor (Belgium))"
    );
});

QUnit.test("invite button should be present on livechat", async (assert) => {
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
        await contains(".o-mail-DiscussSidebarChannel:eq(0)", { text: "Visitor 12" });
        await contains(".o-mail-DiscussSidebarChannel:eq(1)", { text: "Visitor 11" });
        // post a new message on the last channel
        await click(".o-mail-DiscussSidebarChannel:eq(1)");
        await insertText(".o-mail-Composer-input", "Blabla");
        await click(".o-mail-Composer-send:not(:disabled)");
        await contains(".o-mail-DiscussSidebarChannel", { count: 2 });
        await contains(".o-mail-DiscussSidebarChannel:eq(0) span", { text: "Visitor 11" });
        await contains(".o-mail-DiscussSidebarChannel:eq(1) span", { text: "Visitor 12" });
    }
);
