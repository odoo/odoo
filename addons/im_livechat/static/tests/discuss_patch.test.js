import {
    click,
    contains,
    insertText,
    openDiscuss,
    startClient,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { rpcWithEnv } from "@mail/utils/common/misc";
import { test } from "@odoo/hoot";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { defineLivechatModels } from "./livechat_test_helpers";

/** @type {ReturnType<import("@mail/utils/common/misc").rpcWithEnv>} */
let rpc;

defineLivechatModels();

test.skip("add livechat in the sidebar on visitor sending first message", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write([serverState.userId], { im_status: "online" });
    const countryId = pyEnv["res.country"].create({ code: "be", name: "Belgium" });
    const livechatChannelId = pyEnv["im_livechat.channel"].create({
        user_ids: [serverState.userId],
    });
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor (Belgium)" });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor (Belgium)",
        channel_member_ids: [
            Command.create({ is_pinned: false, partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        country_id: countryId,
        livechat_channel_id: livechatChannelId,
        livechat_operator_id: serverState.partnerId,
    });
    const env = await startClient();
    rpc = rpcWithEnv(env);
    await openDiscuss();
    await contains(".o-mail-DiscussSidebar");
    await contains(".o-mail-DiscussSidebarCategory-livechat", { count: 0 });
    // simulate livechat visitor sending a message
    withGuest(guestId, () =>
        rpc("/mail/message/post", {
            post_data: {
                body: "new message",
                message_type: "comment",
                subtype_xmlid: "mail.mt_comment",
            },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-DiscussSidebarCategory-livechat + .o-mail-DiscussSidebarChannel", {
        text: "Visitor (Belgium)",
    });
});

test("invite button should be present on livechat", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 11",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    await startClient();
    await openDiscuss(channelId);
    await contains(".o-mail-Discuss button[title='Add Users']");
});

test.skip("livechats are sorted by last activity time in the sidebar: most recent at the top", async () => {
    const pyEnv = await startServer();
    const guestId_1 = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    const guestId_2 = pyEnv["mail.guest"].create({ name: "Visitor 12" });
    pyEnv["discuss.channel"].create([
        {
            anonymous_name: "Visitor 11",
            channel_member_ids: [
                Command.create({
                    last_interest_dt: "2021-01-01 10:00:00",
                    partner_id: serverState.partnerId,
                }),
                Command.create({ guest_id: guestId_1 }),
            ],
            channel_type: "livechat",
            livechat_operator_id: serverState.partnerId,
        },
        {
            anonymous_name: "Visitor 12",
            channel_member_ids: [
                Command.create({
                    last_interest_dt: "2021-02-01 10:00:00",
                    partner_id: serverState.partnerId,
                }),
                Command.create({ guest_id: guestId_2 }),
            ],
            channel_type: "livechat",
            livechat_operator_id: serverState.partnerId,
        },
    ]);
    await startClient();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel", { count: 2 });
    await contains(":nth-child(1 of .o-mail-DiscussSidebarChannel)", { text: "Visitor 12" });
    await click(":nth-child(2 of .o-mail-DiscussSidebarChannel)", { text: "Visitor 11" });
    await insertText(".o-mail-Composer-input", "Blabla");
    await click(".o-mail-Composer-send:enabled");
    await contains(":nth-child(1 of .o-mail-DiscussSidebarChannel)", { text: "Visitor 11" });
    await contains(":nth-child(2 of .o-mail-DiscussSidebarChannel)", { text: "Visitor 12" });
});
