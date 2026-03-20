import { describe, test } from "@odoo/hoot";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { startServer, start, openDiscuss, contains } from "@mail/../tests/mail_test_helpers";
import { defineHrHolidaysModels } from "@hr_holidays/../tests/hr_holidays_test_helpers";

describe.current.tags("desktop");
defineHrHolidaysModels();

test("thread icon of a chat when correspondent is on leave & online", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", im_status: "online" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    pyEnv["hr.employee"].create({ leave_date_to: "2023-01-01", user_id: userId });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel", {
        contains: [".o-mail-ThreadIcon.fa-plane[title='User is on leave and online']"],
        text: "Demo",
    });
});

test("thread icon of a chat when correspondent is on leave & away", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", im_status: "away" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    pyEnv["hr.employee"].create({ leave_date_to: "2023-01-01", user_id: userId });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel", {
        contains: [".o-mail-ThreadIcon.fa-plane[title='User is on leave and idle']"],
        text: "Demo",
    });
});

test("thread icon of a chat when correspondent is on leave & offline", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", im_status: "offline" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    pyEnv["hr.employee"].create({ leave_date_to: "2023-01-01", user_id: userId });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel", {
        contains: [".o-mail-ThreadIcon.fa-plane[title='User is on leave']"],
        text: "Demo",
    });
});
