import {
    click,
    contains,
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";

import { Command, getService, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("call participants and invitees are grouped in their own box", async () => {
    const pyEnv = await startServer();
    const [aliceUserId, bobUserId] = pyEnv["res.users"].create([
        { name: "Alice", im_status: "online" },
        { name: "Bob", im_status: "online" },
    ]);
    const [alicePartnerId, bobPartnerId, lauriePartnerId] = pyEnv["res.partner"].create([
        { name: "Alice", user_ids: [aliceUserId] },
        { name: "Bob", user_ids: [bobUserId] },
        { name: "Laurie" },
    ]);
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: alicePartnerId }),
            Command.create({ partner_id: bobPartnerId }),
            Command.create({ partner_id: lauriePartnerId }),
        ],
    });
    const [aliceMemberId] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", alicePartnerId],
    ]);
    pyEnv["discuss.channel.rtc.session"].create({
        channel_member_id: aliceMemberId,
        channel_id: channelId,
    });
    const [laurieMemberId] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", lauriePartnerId],
    ]);
    const laurieSessionId = pyEnv["discuss.channel.rtc.session"].create({
        channel_member_id: laurieMemberId,
        channel_id: channelId,
    });
    pyEnv["discuss.channel.member"].write([laurieMemberId], {
        rtc_inviting_session_id: laurieSessionId,
    });
    await start();
    await openDiscuss(channelId);
    await click("[title='Join Call']");
    await contains(".o-discuss-ChannelMemberList");
    await contains(
        ".o-discuss-ChannelMemberList-group h6:text('In this call - 2') + div .o-discuss-ChannelMember:text('Mitchell Admin')"
    );
    await contains(
        ".o-discuss-ChannelMemberList-group h6:text('In this call - 2') + div .o-discuss-ChannelMember:text('Alice')"
    );
    await contains(
        ".o-discuss-ChannelMemberList-group h6:text('Also invited - 1') + div .o-discuss-ChannelMember:text('Laurie')"
    );
    await contains(
        ".o-discuss-ChannelMemberList h6:text('Online - 1') + div .o-discuss-ChannelMember:text('Bob')"
    );
    await contains(".o-discuss-ChannelMemberList-group h6:text('In this call - 2')");
    await contains(".o-discuss-ChannelMemberList-group h6:text('Also invited - 1')");
    await contains(".o-discuss-ChannelMemberList-group h6", { count: 2 });
    // Every member is listed exactly once across the call box and the Online section.
    await contains(".o-discuss-ChannelMember", { count: 4 });
});

test("can see who is talking among call participants", async () => {
    const pyEnv = await startServer();
    const [aliceUserId, bobUserId] = pyEnv["res.users"].create([
        { name: "Alice", im_status: "online" },
        { name: "Bob", im_status: "online" },
    ]);
    const [alicePartnerId, bobPartnerId] = pyEnv["res.partner"].create([
        { name: "Alice", user_ids: [aliceUserId] },
        { name: "Bob", user_ids: [bobUserId] },
    ]);
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: alicePartnerId }),
            Command.create({ partner_id: bobPartnerId }),
        ],
    });
    const [aliceMemberId] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", channelId],
        ["partner_id", "=", alicePartnerId],
    ]);
    const aliceSessionId = pyEnv["discuss.channel.rtc.session"].create({
        channel_member_id: aliceMemberId,
        channel_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await click("[title='Join Call']");
    // Talking indicator shows up while Alice is actually talking.
    const store = getService("mail.store");
    store["discuss.channel.rtc.session"].get(aliceSessionId).isTalking = true;
    await contains(
        ".o-discuss-ChannelMember:has(:text('Alice')) .o-mail-DiscussAvatar.o-isTalking"
    );
});
