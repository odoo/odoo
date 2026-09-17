import { describe, test } from "@odoo/hoot";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import {
    click,
    contains,
    openMessagingMenu,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { defineHrHolidaysModels } from "@hr_holidays/../tests/hr_holidays_test_helpers";

describe.current.tags("desktop");
defineHrHolidaysModels();

test("shows 'Back on' in chat window header of dm chat", async () => {
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
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openMessagingMenu();
    await click(".o-mail-NotificationItem");
    await contains(
        ".o-mail-ChatWindow-header .o-mail-ChatWindow-outOfOffice:text('Back on Jan 1, 2023')"
    );
});
