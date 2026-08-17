import { defineCalendarModels } from "@calendar/../tests/calendar_test_helpers";
import { contains, openDiscuss, start, startServer } from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { serializeDateTime } from "@web/core/l10n/dates";

describe.current.tags("desktop");
defineCalendarModels();

const { DateTime } = luxon;

test("meeting status is shown in discuss chat", async () => {
    mockDate("2025-04-08 12:00:00", 0);
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const stop = DateTime.now().plus({ hours: 1 });
    const eventId = pyEnv["calendar.event"].create({
        name: "Meeting",
        start: serializeDateTime(DateTime.now()),
        stop: serializeDateTime(stop),
        show_as: "busy",
        privacy: "public",
    });
    pyEnv["calendar.attendee"].create({
        event_id: eventId,
        partner_id: partnerId,
        state: "accepted",
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
    await contains(".o-mail-DiscussContent-threadName", { value: "Demo" });
    await contains(".o-mail-DiscussContent-header .text-warning", {
        text: `In a meeting until ${stop.toLocaleString(DateTime.TIME_SIMPLE)}`,
    });
});
