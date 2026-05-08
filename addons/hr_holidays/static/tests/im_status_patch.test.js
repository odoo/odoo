import { describe, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { startServer, start, openDiscuss } from "@mail/../tests/mail_test_helpers";
import { defineHrHolidaysModels } from "@hr_holidays/../tests/hr_holidays_test_helpers";

describe.current.tags("desktop");
defineHrHolidaysModels();

const { DateTime } = luxon;

test("on leave & online", async () => {
    mockDate("2025-04-08 12:00:00");
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId, im_status: "online" });
    pyEnv["hr.employee"].create({
        leave_date_to: DateTime.now().plus({ days: 3 }).toISODate(),
        user_id: userId,
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
        ".o-mail-DiscussContent-header .o-mail-ImStatus[data-icon='travel'][title^='User is on leave and online ·']:count(1)"
    );
});

test("on leave & away", async () => {
    mockDate("2025-04-08 12:00:00");
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId, im_status: "away" });
    pyEnv["hr.employee"].create({
        leave_date_to: DateTime.now().plus({ days: 3 }).toISODate(),
        user_id: userId,
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
        ".o-mail-DiscussContent-header .o-mail-ImStatus[data-icon='travel'][title^='User is on leave and idle ·']:count(1)"
    );
});

test("on leave & offline", async () => {
    mockDate("2025-04-08 12:00:00");
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId, im_status: "offline" });
    pyEnv["hr.employee"].create({
        leave_date_to: DateTime.now().plus({ days: 3 }).toISODate(),
        user_id: userId,
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
        ".o-mail-DiscussContent-header .o-mail-ImStatus[data-icon='travel'][title^='User is on leave ·']:count(1)"
    );
});
