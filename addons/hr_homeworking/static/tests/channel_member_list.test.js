import { describe, expect, test } from "@odoo/hoot";
import {
    contains,
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { Command, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

async function openChannelWith(im_status) {
    const pyEnv = await startServer();
    pyEnv["res.partner"].write([serverState.partnerId], { im_status: "online" });
    const partnerId = pyEnv["res.partner"].create({ name: "Homeworker", im_status });
    pyEnv["res.users"].create({ name: "Homeworker", partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-ChannelMemberList");
}

test("a control: a plainly offline member is an offline member", async () => {
    await openChannelWith("offline");
    expect(".o-discuss-ChannelMember").toHaveCount(2);
    expect(".o-discuss-ChannelMember.o-offline").toHaveCount(1);
});

test("an employee online from home is an online member, not an offline one", async () => {
    await openChannelWith("home_online");
    expect(".o-discuss-ChannelMember").toHaveCount(2);
    expect(".o-discuss-ChannelMember.o-offline").toHaveCount(0);
});

test("an employee busy at the office is an online member", async () => {
    await openChannelWith("office_busy");
    expect(".o-discuss-ChannelMember.o-offline").toHaveCount(0);
});

test("an employee offline from home is still an offline member", async () => {
    await openChannelWith("home_offline");
    expect(".o-discuss-ChannelMember.o-offline").toHaveCount(1);
});
