import { describe, test } from "@odoo/hoot";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { contains, openDiscuss, start, startServer } from "@mail/../tests/mail_test_helpers";
import { defineHrHolidaysModels } from "@hr_holidays/../tests/hr_holidays_test_helpers";

describe.current.tags("desktop");
defineHrHolidaysModels();

test("on leave members are categorised correctly in online/offline", async () => {
    const pyEnv = await startServer();
    const [partnerId1, partnerId2, partnerId3] = pyEnv["res.partner"].create([
        { name: "Online Partner", im_status: "online" },
        { name: "On Leave Online", im_status: "leave_online" },
        { name: "On Leave Idle", im_status: "leave_away" },
    ]);
    pyEnv["res.partner"].write([serverState.partnerId], { im_status: "leave_offline" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "TestChanel",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId1 }),
            Command.create({ partner_id: partnerId2 }),
            Command.create({ partner_id: partnerId3 }),
        ],
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-ChannelMemberList h6", { text: "Online - 3" });
    await contains(".o-discuss-ChannelMemberList h6", { text: "Offline - 1" });
});
