import { describe, test } from "@odoo/hoot";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { startServer, start, openDiscuss, contains } from "@mail/../tests/mail_test_helpers";
import { defineHrHolidaysModels } from "@hr_holidays/../tests/hr_holidays_test_helpers";
import { mockDate } from "@odoo/hoot-mock";

describe.current.tags("desktop");
defineHrHolidaysModels();

test("out of office message on direct chat with out of office partner", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Demo",
        im_status: "leave_online",
        out_of_office_date_end: "2023-01-01",
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

test("Should display 'Out of Office' due to a public holiday", async () => {
    mockDate("2023-01-01 12:00:00");
    const pyEnv = await startServer();
    const companyId = pyEnv["res.company"].create({
        name: "Temporary Company",
    });
    const partnerId = pyEnv["res.partner"].create({
        name: "Demo",
    });
    pyEnv["res.users"].create({
        partner_id: partnerId,
        company_id: companyId,
    });
    pyEnv["resource.calendar.leaves"].create({
        name: "Diwali",
        date_from: "2023-01-01",
        date_to: "2023-01-01",
        company_id: companyId,
        resource_id: false,
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
    await contains(".alert", { text: "Out of office due to Diwali (Public Holiday)." });
});
