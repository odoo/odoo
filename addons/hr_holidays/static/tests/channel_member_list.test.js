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
        { name: "On Leave Online", im_status: "online" },
        { name: "On Leave Idle", im_status: "away" },
    ]);
    pyEnv["res.users"].write([serverState.userId], { leave_date_to: "2023-01-02" });
    pyEnv["res.users"].create({ partner_id: partnerId2, leave_date_to: "2023-01-03" });
    pyEnv["res.users"].create({ partner_id: partnerId3, leave_date_to: "2023-01-04" });
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
