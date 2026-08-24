import { defineCalendarModels } from "@calendar/../tests/calendar_test_helpers";

import {
    click,
    contains,
    MENU_ACTIVE_IDS,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";

import { describe, expect, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";

import { getOrigin } from "@web/core/utils/urls";
import { Command, getService, patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineCalendarModels();

test("meeting action is a dropdown offering to start or schedule a meeting", async () => {
    await startServer();
    await start();
    await openDiscuss(MENU_ACTIVE_IDS.MEETING);
    await click(".o-mail-MessagingMenu-searchRow .btn");
    await contains(".o-dropdown-item", { count: 2 });
    await contains(".o-dropdown-item:text('Start Now')");
    await contains(".o-dropdown-item:text('Schedule for later')");
});

test("scheduling a meeting leaves for the calendar, video call in hand", async () => {
    await startServer();
    await start();
    await openDiscuss(MENU_ACTIVE_IDS.MEETING);
    patchWithCleanup(getService("action"), {
        doAction(action, options) {
            expect.step("do_action");
            expect(action).toBe("calendar.action_calendar_event");
            expect(options.additionalContext).toEqual({
                default_access_token: "testtoken",
                default_videocall_location: `${getOrigin()}/calendar/join_videocall/testtoken`,
                return_to_parent_breadcrumb: true,
            });
        },
    });
    await click(".o-mail-MessagingMenu-searchRow .btn");
    await click(".o-dropdown-item:text('Schedule for later')");
    // the slot is picked in the calendar, whose quick create prefills the rest from it
    await expect.waitForSteps(["do_action"]);
});

test("meetings tab opens on the meetings of today", async () => {
    mockDate("2026-03-11 10:30:00", +0);
    const pyEnv = await startServer();
    const demoChannelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "group",
        default_display_mode: "video_full_screen",
        name: "Product Demo",
    });
    pyEnv["calendar.event"].create({
        name: "Product Demo",
        start: "2026-03-11 14:00:00",
        stop: "2026-03-11 15:00:00",
        videocall_channel_id: demoChannelId,
    });
    const syncChannelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "group",
        default_display_mode: "video_full_screen",
        name: "Weekly Sync",
    });
    pyEnv["calendar.event"].create({
        name: "Weekly Sync",
        start: "2026-03-12 14:00:00",
        stop: "2026-03-12 15:00:00",
        videocall_channel_id: syncChannelId,
    });
    // an ad-hoc meeting ("Start Now") takes place the day its channel is created
    pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "group",
        default_display_mode: "video_full_screen",
        name: "Ad-hoc Call",
    });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "group",
        create_date: "2026-03-10 09:00:00",
        default_display_mode: "video_full_screen",
        name: "Yesterday Call",
    });
    await start();
    await openDiscuss(MENU_ACTIVE_IDS.MEETING);
    await contains(".o-mail-MessagingMenu-filter.o-active:text('Today')");
    await contains(".o-mail-NotificationItem", { count: 2 });
    await contains(".o-mail-NotificationItem-name:has(:text('Product Demo'))");
    await contains(".o-mail-NotificationItem-name:has(:text('Ad-hoc Call'))");
    await click(".o-mail-MessagingMenu-filter:text('All')");
    await contains(".o-mail-NotificationItem", { count: 4 });
});

test("meeting name is followed by the time it starts at", async () => {
    mockDate("2026-03-11 10:30:00", +0);
    const pyEnv = await startServer();
    for (const [name, start, stop] of [
        ["Demo", "2026-03-11 14:00:00", "2026-03-11 15:00:00"],
        ["Retro", "2025-12-18 09:00:00", "2025-12-18 10:00:00"],
    ]) {
        const channelId = pyEnv["discuss.channel"].create({
            channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
            channel_type: "group",
            default_display_mode: "video_full_screen",
            name,
        });
        pyEnv["calendar.event"].create({ name, start, stop, videocall_channel_id: channelId });
    }
    await start();
    await openDiscuss(MENU_ACTIVE_IDS.MEETING);
    await click(".o-mail-MessagingMenu-filter:text('All')");
    const meetingStart = ".o-mail-MessagingMenuItem-meetingStart";
    const row = (name) => `.o-mail-NotificationItem:has(:text('${name}'))`;
    await contains(`${row("Demo")} ${meetingStart}:text('@ 2:00 PM')`);
    // a meeting of another day is shown by its time as well
    await contains(`${row("Retro")} ${meetingStart}:text('@ 9:00 AM')`);
});

test("meetings are listed as an agenda, the ones already over at the bottom", async () => {
    mockDate("2026-03-11 10:30:00", +0);
    const pyEnv = await startServer();
    for (const [name, start, stop] of [
        ["Standup", "2026-03-11 09:00:00", "2026-03-11 09:30:00"],
        ["Product Demo", "2026-03-11 10:00:00", "2026-03-11 11:00:00"],
        ["Design Review", "2026-03-11 14:00:00", "2026-03-11 15:00:00"],
        ["Weekly Sync", "2026-03-12 14:00:00", "2026-03-12 15:00:00"],
    ]) {
        const channelId = pyEnv["discuss.channel"].create({
            channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
            channel_type: "group",
            default_display_mode: "video_full_screen",
            name,
        });
        pyEnv["calendar.event"].create({ name, start, stop, videocall_channel_id: channelId });
    }
    await start();
    await openDiscuss(MENU_ACTIVE_IDS.MEETING);
    // the meeting going on comes first, "Standup" is over
    await contains(".o-mail-NotificationItem-name:eq(0):has(:text('Product Demo'))");
    await contains(".o-mail-NotificationItem-name:eq(1):has(:text('Design Review'))");
    await contains(".o-mail-NotificationItem-name:eq(2):has(:text('Standup'))");
    await click(".o-mail-MessagingMenu-filter:text('All')");
    await contains(".o-mail-NotificationItem-name:eq(0):has(:text('Product Demo'))");
    await contains(".o-mail-NotificationItem-name:eq(1):has(:text('Design Review'))");
    await contains(".o-mail-NotificationItem-name:eq(2):has(:text('Weekly Sync'))");
    await contains(".o-mail-NotificationItem-name:eq(3):has(:text('Standup'))");
});

test("a favorite meeting stays on top, whenever it takes place", async () => {
    mockDate("2026-03-11 10:30:00", +0);
    const pyEnv = await startServer();
    for (const [name, start, stop, isFavorite] of [
        ["Product Demo", "2026-03-11 14:00:00", "2026-03-11 15:00:00", false],
        ["Standup", "2026-03-11 09:00:00", "2026-03-11 09:30:00", true],
    ]) {
        const channelId = pyEnv["discuss.channel"].create({
            channel_member_ids: [
                Command.create({ is_favorite: isFavorite, partner_id: serverState.partnerId }),
            ],
            channel_type: "group",
            default_display_mode: "video_full_screen",
            name,
        });
        pyEnv["calendar.event"].create({ name, start, stop, videocall_channel_id: channelId });
    }
    await start();
    await openDiscuss(MENU_ACTIVE_IDS.MEETING);
    await contains(".o-mail-NotificationItem-name:eq(0):has(:text('Standup'))");
    await contains(".o-mail-NotificationItem-name:eq(1):has(:text('Product Demo'))");
});

test("today filter comes right after All, before the mail filters", async () => {
    mockDate("2026-03-11 10:30:00", +0);
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "group",
        default_display_mode: "video_full_screen",
        name: "Product Demo",
    });
    pyEnv["calendar.event"].create({
        name: "Product Demo",
        start: "2026-03-11 14:00:00",
        stop: "2026-03-11 15:00:00",
        videocall_channel_id: channelId,
    });
    await start();
    await openDiscuss(MENU_ACTIVE_IDS.MEETING);
    await contains(".o-mail-MessagingMenu-filter", { count: 4 });
    await contains(".o-mail-MessagingMenu-filter:eq(0):text('All')");
    await contains(".o-mail-MessagingMenu-filter:eq(1):text('Today')");
    await contains(".o-mail-MessagingMenu-filter:eq(2):text('Unread')");
    await contains(".o-mail-MessagingMenu-filter:eq(3):text('Thread')");
});

test("today filter is only offered on the meetings tab", async () => {
    mockDate("2026-03-11 10:30:00", +0);
    const pyEnv = await startServer();
    const meetingChannelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "group",
        default_display_mode: "video_full_screen",
        name: "Product Demo",
    });
    pyEnv["calendar.event"].create({
        name: "Product Demo",
        start: "2026-03-11 14:00:00",
        stop: "2026-03-11 15:00:00",
        videocall_channel_id: meetingChannelId,
    });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "group",
        name: "Sales Team",
    });
    await start();
    await openDiscuss(MENU_ACTIVE_IDS.MEETING);
    await contains(".o-mail-MessagingMenu-filter:text('Today')");
    await click(".o-mail-MessagingMenu-tab[data-id='chat']");
    await contains(".o-mail-MessagingMenu-filter", { count: 3 });
    await contains(".o-mail-MessagingMenu-filter:text('All')");
    await contains(".o-mail-MessagingMenu-filter:text('Unread')");
    await contains(".o-mail-MessagingMenu-filter:text('Group')");
});
