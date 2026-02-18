import { describe, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { startServer, start, openDiscuss, contains } from "@mail/../tests/mail_test_helpers";
import { defineHrHolidaysModels } from "@hr_holidays/../tests/hr_holidays_test_helpers";
import { serializeDateTime } from "@web/core/l10n/dates";

describe.current.tags("desktop");
defineHrHolidaysModels();
const { DateTime } = luxon;

test("out of office message on direct chat with out of office partner", async () => {
    mockDate("2022-12-20 12:00:00");
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo", im_status: "online" });
    const userId = pyEnv["res.users"].create({ partner_id: partnerId });
    const employee = pyEnv["hr.employee"].create({
        user_id: userId,
        leave_date_from: serializeDateTime(DateTime.now().plus({ days: 2 })),
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
    await contains(".alert", { text: "Back on Jan 1, 2023" });
});
