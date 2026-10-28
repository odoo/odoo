import { describe, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { mockTimeZone } from "@odoo/hoot-mock";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { startServer, start, openDiscuss } from "@mail/../tests/mail_test_helpers";
import { defineHrHolidaysModels } from "@hr_holidays/../tests/hr_holidays_test_helpers";

describe.current.tags("desktop");
defineHrHolidaysModels();

test("show 'Back on' in header of dm chat", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId, im_status: "online" });
    const employee = pyEnv["hr.employee"].create({
        user_id: userId,
        leave_date_to: "2023-01-01",
    });
    pyEnv["res.users"].write([userId], {
        employee_ids: [Command.link(employee)],
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(
        ".o-mail-DiscussContent-header .o-mail-DiscussContent-outOfOffice:text('Back on Jan 1, 2023'):count(1)"
    );
});

test("show 'Back on' in header of dm chat even when showing local timezone", async () => {
    mockTimeZone(-7);
    const pyEnv = await startServer();
    pyEnv["res.partner"].write([serverState.partnerId], { tz: "America/Los_Angeles" });
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", tz: "Europe/Brussels" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId, im_status: "online" });
    const employee = pyEnv["hr.employee"].create({
        user_id: userId,
        leave_date_to: "2023-01-03",
    });
    pyEnv["res.users"].write([userId], {
        employee_ids: [Command.link(employee)],
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-DiscussContent-header .o-mail-DiscussContent-localDateTime:count(1)");
    await waitFor(
        ".o-mail-DiscussContent-header .o-mail-DiscussContent-outOfOffice:text('Back on Jan 3, 2023'):count(1)"
    );
});
