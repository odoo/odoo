import { defineCalendarModels } from "@calendar/../tests/calendar_test_helpers";
import {
    click,
    contains,
    openDiscuss,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { insertTextInComposer } from "@mail/../tests/mail_test_helpers_composer";
import { advanceTime, describe, test } from "@odoo/hoot";
import { press } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { serializeDateTime } from "@web/core/l10n/dates";

describe.current.tags("desktop");
defineCalendarModels();

const { DateTime } = luxon;

function createMeeting(pyEnv, { startIn = 0 } = {}) {
    const start = DateTime.now().plus({ minutes: startIn });
    const stop = start.plus({ hours: 1 });
    const eventId = pyEnv["calendar.event"].create({
        name: "Meeting",
        start: serializeDateTime(start),
        stop: serializeDateTime(stop),
        privacy: "public",
        show_as: "busy",
        allday: false,
    });
    pyEnv["calendar.attendee"].create({
        event_id: eventId,
        partner_id: serverState.partnerId,
        state: "accepted",
    });
    return stop;
}

test("Show meeting status in avatar card", async () => {
    mockDate("2025-04-08 12:00:00");
    const pyEnv = await startServer();
    const stop = createMeeting(pyEnv);
    const fakeId = pyEnv["res.fake"].create({ name: "Salutations, voyageur" });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "not empty",
        model: "res.fake",
        res_id: fakeId,
        subject: "Another Subject",
    });
    await start();
    await openFormView("res.fake", fakeId);
    await click(".o-mail-Message-avatar");
    await contains(".o_avatar_card span", {
        text: `In a meeting until ${stop.toLocaleString(DateTime.TIME_SIMPLE)}`,
    });
});

test("Show meeting status in mention list", async () => {
    mockDate("2025-04-08 12:00:00");
    const pyEnv = await startServer();
    const stop = createMeeting(pyEnv);
    const channelId = pyEnv["discuss.channel"].create({
        name: "General & good",
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
    });
    await start();
    await openDiscuss(channelId);
    await insertTextInComposer(".o-mail-Composer", "@");
    await contains(".o-mail-NavigableList-item .text-success", {
        text: `In a meeting until ${stop.toLocaleString(DateTime.TIME_SIMPLE)}`,
    });
});

test("Discuss Sidebar shows meeting status", async () => {
    mockDate("2025-04-08 12:00:00");
    const pyEnv = await startServer();
    createMeeting(pyEnv);
    const stop = createMeeting(pyEnv, { startIn: 60 }); // back-to-back: busy until its end
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-NotificationItem .text-success", {
        text: `In a meeting until ${stop.toLocaleString(DateTime.TIME_SIMPLE)}`,
    });
});

test("CTRL+K command shows meeting status", async () => {
    mockDate("2025-04-08 12:00:00");
    const pyEnv = await startServer();
    const stop = createMeeting(pyEnv);
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Discuss[data-active]");
    await press(["ctrl", "k"]);
    await contains(".o-mail-DiscussCommand .text-success", {
        text: `In a meeting until ${stop.toLocaleString(DateTime.TIME_SIMPLE)}`,
    });
});

test("Meeting status shows once a meeting starts after loading", async () => {
    mockDate("2025-04-08 12:00:00");
    const pyEnv = await startServer();
    const stop = createMeeting(pyEnv, { startIn: 30 });
    // the next meeting starts 4 seconds after the first one ends
    const nextStop = createMeeting(pyEnv, { startIn: 90 + 4 / 60 });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    const text = `In a meeting until ${stop.toLocaleString(DateTime.TIME_SIMPLE)}`;
    const nextText = `In a meeting until ${nextStop.toLocaleString(DateTime.TIME_SIMPLE)}`;
    await contains(".o-mail-NotificationItem");
    await contains(".o-mail-NotificationItem .text-success", { text, count: 0 });
    await advanceTime(30 * 60 * 1000);
    await contains(".o-mail-NotificationItem .text-success", { text });
    await advanceTime(60 * 60 * 1000);
    await contains(".o-mail-NotificationItem .text-success", { text, count: 0 });
    // it shows without fetching the partner again
    await advanceTime(4 * 1000);
    await contains(".o-mail-NotificationItem .text-success", { text: nextText });
});
