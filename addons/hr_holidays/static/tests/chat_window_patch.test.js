import { describe, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";
import { Command, getService, serverState } from "@web/../tests/web_test_helpers";
import { click, openMessagingMenu, start, startServer } from "@mail/../tests/mail_test_helpers";
import { defineHrHolidaysModels } from "@hr_holidays/../tests/hr_holidays_test_helpers";

describe.current.tags("desktop");
defineHrHolidaysModels();

const { DateTime } = luxon;

test("shows 'Back on' in chat window header of dm chat", async () => {
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
    await waitFor(
        ".o-mail-ChatWindow-header .o-mail-ChatWindow-statusSubtitle:text('Back on Apr 11'):count(1)"
    );
});

test("shows both 'Back on' and the status message in chat window header", async () => {
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
    await waitFor(
        ".o-mail-ChatWindow-header .o-mail-ChatWindow-statusSubtitle:text('Back on Apr 11 · Ask Mitchell meanwhile'):count(1)"
    );
    await waitFor(
        ".o-mail-ChatWindow-statusSubtitle .text-warning:text('Back on Apr 11') +.text-muted:text('Ask Mitchell meanwhile')"
    );
});

test("meeting status takes precedence over 'Back on' in chat window header", async () => {
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
    await waitFor(".o-mail-ChatWindow-statusSubtitle:text('Back on Apr 11')");
    // the meeting status is computed by calendar's server code, not by this mock server
    const meetingUntil = DateTime.now().plus({ hours: 1 });
    getService("mail.store")["res.partner"].insert({
        id: partnerId,
        upcoming_meeting_ids: [{ id: 1, start: DateTime.now(), stop: meetingUntil }],
    });
    const time = meetingUntil.toLocaleString(DateTime.TIME_SIMPLE);
    // the whole subtitle is the meeting status: 'Back on' is hidden
    await waitFor(`.o-mail-ChatWindow-statusSubtitle:text('In a meeting until ${time}')`);
});
