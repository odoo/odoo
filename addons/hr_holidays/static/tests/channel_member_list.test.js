import { describe, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import {
    actionPanel,
    contains,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { defineHrHolidaysModels } from "@hr_holidays/../tests/hr_holidays_test_helpers";

describe.current.tags("desktop");
defineHrHolidaysModels();

test("on leave members are categorised correctly in online/offline", async () => {
    mockDate("2022-12-30 12:00:00");
    const pyEnv = await startServer();
    const [partnerId1, partnerId2, partnerId3, partnerId4] = pyEnv["res.partner"].create([
        { name: "Online Partner" },
        { name: "On Leave Online" },
        { name: "On Leave Idle" },
        { name: "On Leave Offline" },
    ]);
    const [, userId2, userId3, userId4] = pyEnv["res.users"].create([
        { partner_id: partnerId1, im_status: "online" },
        { partner_id: partnerId2, im_status: "online" },
        { partner_id: partnerId3, im_status: "away" },
        { partner_id: partnerId4, im_status: "offline" },
    ]);
    pyEnv["hr.employee"].create([
        { user_id: userId2, leave_datetime_to: "2023-01-03 08:00:00" },
        { user_id: userId3, leave_datetime_to: "2023-01-04 08:00:00" },
        { user_id: userId4, leave_datetime_to: "2023-01-05 08:00:00" },
    ]);
    const channelId = pyEnv["discuss.channel"].create({
        name: "TestChanel",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId1 }),
            Command.create({ partner_id: partnerId2 }),
            Command.create({ partner_id: partnerId3 }),
            Command.create({ partner_id: partnerId4 }),
        ],
        channel_type: "channel",
    });
    await start();
    await openDiscuss(channelId);
    await contains(`${actionPanel("Members")} h6`, { text: "Online - 4" });
    await contains(`${actionPanel("Members")} h6`, { text: "Offline - 1" });
});
