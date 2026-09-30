import { click, contains, openDiscuss, start, startServer } from "@mail/../tests/mail_test_helpers";
import { describe, expect, test, waitFor } from "@odoo/hoot";
import { waitForNone } from "@odoo/hoot-dom";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { defineLivechatModels } from "@im_livechat/../tests/livechat_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test("display country in channel member list", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "James" });
    pyEnv["res.partner"].create({
        name: "James",
        user_ids: [userId],
    });
    const countryId = pyEnv["res.country"].create({ code: "be", name: "Belgium" });
    const guestId = pyEnv["mail.guest"].create({
        name: "Visitor #20",
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        country_id: countryId,
        channel_type: "livechat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-ActionPanel:contains(Information)");
    await click(".o-mail-DiscussContent-header button[name='member-list']");
    await contains(".o-discuss-ChannelMember span", { text: "Belgium", count: 2 });
});

test("live chat members show no role crown nor role actions", async () => {
    const pyEnv = await startServer();
    const [demoPid, jamesPid] = pyEnv["res.partner"].create([{ name: "Demo" }, { name: "James" }]);
    pyEnv["res.users"].create([
        { partner_id: demoPid, active: true },
        { partner_id: jamesPid, active: true },
    ]);
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor #20" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, channel_role: "owner" }),
            Command.create({ partner_id: demoPid, channel_role: "admin" }),
            Command.create({ partner_id: jamesPid }),
        ],
        channel_type: "channel",
    });
    const livechatId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ partner_id: jamesPid, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        channel_type: "livechat",
    });
    const livechatMembers = pyEnv["discuss.channel.member"].search_read([
        ["channel_id", "=", livechatId],
    ]);
    expect(livechatMembers.map((member) => member.channel_role)).toEqual(["owner", "owner", false]);
    await start();
    // roles are shown in regular channels
    await openDiscuss(channelId);
    await waitFor(".o-discuss-ChannelMember:count(3)");
    expect(".o-discuss-ChannelMember [data-icon='crown_f'][title='Owner']").toHaveCount(1);
    expect(".o-discuss-ChannelMember [data-icon='crown'][title='Admin']").toHaveCount(1);
    await click(".o-discuss-ChannelMember:contains(James) [title='Member Actions']");
    await waitFor(".o-dropdown-item:count(3)");
    expect(".o-dropdown-item:contains(Set Owner)").toHaveCount(1);
    expect(".o-dropdown-item:contains(Set Admin)").toHaveCount(1);
    expect(".o-dropdown-item:contains(Remove Member)").toHaveCount(1);
    // but not in live chats, even though agents are owners
    await openDiscuss(livechatId);
    await waitFor(".o-livechat-ChannelInfoList"); // wait for auto-open of this panel
    await click("button[title='Members']");
    await waitFor(".o-discuss-ChannelMember:count(3)");
    expect(".o-discuss-ChannelMember [data-icon='crown_f']").toHaveCount(0);
    expect(".o-discuss-ChannelMember [data-icon='crown']").toHaveCount(0);
    await click(".o-discuss-ChannelMember:contains(James) [title='Member Actions']");
    await waitFor(".o-dropdown-item:contains(Remove Member)");
    expect(".o-dropdown-item").toHaveCount(1);
    await click(".o-mail-Thread");
    await waitForNone(".o-dropdown-item");
    await click(".o-discuss-ChannelMember:contains(Visitor #20) [title='Member Actions']");
    await waitFor(".o-dropdown-item:contains(Remove Member)");
    expect(".o-dropdown-item").toHaveCount(1);
});
