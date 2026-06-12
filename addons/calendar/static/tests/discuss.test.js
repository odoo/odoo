/** @odoo-module **/

import { test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { defineCalendarModels } from "@calendar/../tests/calendar_test_helpers";
import { contains, openDiscuss, start, startServer } from "@mail/../tests/mail_test_helpers";
import { Command, serverState } from "@web/../tests/web_test_helpers";

const { DateTime } = luxon;

defineCalendarModels();

test("meeting status should be displayed in discuss content header", async () => {
    mockDate("2025-04-08 12:00:00");
    const pyEnv = await startServer();
    const inMeetingUntil = DateTime.now().plus({ hours: 1 }).toFormat("yyyy-MM-dd HH:mm:ss");
    const UserId = pyEnv["res.users"].create({
        name: "User A",
        in_meeting_until: inMeetingUntil,
    });
    const PartnerId = pyEnv["res.partner"].create({
        name: "User A",
        main_user_id: UserId,
    });
    pyEnv["res.users"].write([UserId], { partner_id: PartnerId });
    const currentPartnerId = serverState.partnerId;
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "chat",
        name: "Chat with User A",
        channel_member_ids: [
            Command.create({
                partner_id: currentPartnerId,
            }),
            Command.create({
                partner_id: PartnerId,
            }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    const expectedTime = DateTime.fromSQL(inMeetingUntil, { zone: "utc" })
        .toLocal()
        .toLocaleString(DateTime.TIME_SIMPLE);
    await contains(".o-mail-DiscussContent-meetingStatus", {
        text: `In a meeting until ${expectedTime}`,
    });
});
