import { describe, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { mockDate, mockTimeZone } from "@odoo/hoot-mock";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { startServer, start, openDiscuss } from "@mail/../tests/mail_test_helpers";
import { defineHrHolidaysModels } from "@hr_holidays/../tests/hr_holidays_test_helpers";

describe.current.tags("desktop");
defineHrHolidaysModels();

const { DateTime } = luxon;

test("show 'Back on' in header of dm chat", async () => {
    mockDate("2025-04-08 12:00:00");
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId, im_status: "online" });
    const employee = pyEnv["hr.employee"].create({
        user_id: userId,
        leave_date_to: DateTime.now().plus({ days: 3 }).toISODate(),
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
        ".o-mail-DiscussContent-header .o-mail-DiscussContent-statusSubtitle:text('Back on Apr 11'):count(1)"
    );
});

test("show 'Back on' in header of dm chat even when showing local timezone", async () => {
    mockDate("2025-04-08 12:00:00");
    mockTimeZone(-7);
    const pyEnv = await startServer();
    pyEnv["res.partner"].write([serverState.partnerId], { tz: "America/Los_Angeles" });
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", tz: "Europe/Brussels" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId, im_status: "online" });
    const employee = pyEnv["hr.employee"].create({
        user_id: userId,
        leave_date_to: DateTime.now().plus({ days: 3 }).toISODate(),
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
        ".o-mail-DiscussContent-header .o-mail-DiscussContent-statusSubtitle:text('Back on Apr 11'):count(1)"
    );
});

test("shows both 'Back on' and the status message in header of dm chat", async () => {
    mockDate("2025-04-08 12:00:00");
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const userId = pyEnv["res.users"].create({
        im_status: "online",
        partner_id: partnerId,
        status_message: "Ask Mitchell meanwhile",
    });
    const employee = pyEnv["hr.employee"].create({
        user_id: userId,
        leave_date_to: DateTime.now().plus({ days: 3 }).toISODate(),
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
        ".o-mail-DiscussContent-header .o-mail-DiscussContent-statusSubtitle:text('Back on Apr 11 · Ask Mitchell meanwhile'):count(1)"
    );
    await waitFor(
        ".o-mail-DiscussContent-statusSubtitle .text-warning:text('Back on Apr 11') + .text-muted:text('Ask Mitchell meanwhile')"
    );
});
