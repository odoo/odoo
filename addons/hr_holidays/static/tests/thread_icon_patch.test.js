import { describe, test } from "@odoo/hoot";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { startServer, start, openDiscuss, contains } from "@mail/../tests/mail_test_helpers";
import { defineHrHolidaysModels } from "@hr_holidays/../tests/hr_holidays_test_helpers";

describe.current.tags("desktop");
defineHrHolidaysModels();

test("thread icon of a chat when correspondent is on leave & online", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ im_status: "online", name: "Demo" });
    pyEnv["res.users"].create({ partner_id: partnerId, leave_date_to: "2023-01-01" });
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
        contains: [".o-mail-ThreadIcon .fa-plane[title='On Leave (Online)']"],
        text: "Demo",
    });
});

test("thread icon of a chat when correspondent is on leave & away", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ im_status: "away", name: "Demo" });
    pyEnv["res.users"].create({ partner_id: partnerId, leave_date_to: "2023-01-01" });
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
        contains: [".o-mail-ThreadIcon .fa-plane[title='On Leave (Idle)']"],
        text: "Demo",
    });
});

test("thread icon of a chat when correspondent is on leave & offline", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ im_status: "offline", name: "Demo" });
    pyEnv["res.users"].create({ partner_id: partnerId, leave_date_to: "2023-01-01" });
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
        contains: [".o-mail-ThreadIcon .fa-plane[title='On Leave']"],
        text: "Demo",
    });
});
