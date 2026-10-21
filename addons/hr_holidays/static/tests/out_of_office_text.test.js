import { describe, test } from "@odoo/hoot";

import {
    startServer,
    start,
    click,
    openFormView,
    contains,
    openDiscuss,
} from "@mail/../tests/mail_test_helpers";
import { insertTextInComposer } from "@mail/../tests/mail_test_helpers_composer";

import { defineHrHolidaysModels } from "@hr_holidays/../tests/hr_holidays_test_helpers";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { serializeDateTime } from "@web/core/l10n/dates";
import { advanceTime, press } from "@odoo/hoot-dom";
import { mockDate, mockTimeZone } from "@odoo/hoot-mock";

describe.current.tags("desktop");
defineHrHolidaysModels();

const { DateTime } = luxon;

test("Show 'back on' in avatar card", async () => {
    mockDate("2025-04-08 12:00:00");
    const pyEnv = await startServer();
    const employee = pyEnv["hr.employee"].create({
        user_id: serverState.userId,
        work_contact_id: serverState.partnerId,
        leave_datetime_to: serializeDateTime(DateTime.now().plus({ days: 3 })),
    });
    pyEnv["res.users"].write([serverState.userId], {
        employee_ids: [Command.link(employee)],
    });

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
    await contains(".o_avatar_card span", { text: "Back on Apr 11" });
});

test("Show 'back on' in mention list", async () => {
    mockDate("2025-04-08 12:00:00");
    const pyEnv = await startServer();
    const employee = pyEnv["hr.employee"].create({
        user_id: serverState.userId,
        leave_datetime_to: serializeDateTime(DateTime.now().plus({ days: 3 })),
    });
    pyEnv["res.users"].write([serverState.userId], {
        employee_ids: [Command.link(employee)],
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "General & good",
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
    });
    await start();
    await openDiscuss(channelId);
    await insertTextInComposer(".o-mail-Composer", "@");
    await contains(".o-mail-NavigableList-item span", { text: "Back on Apr 11" });
});

test("Show year when 'back on' is on different year than now", async () => {
    mockDate("2024-12-20 12:00:00");
    const pyEnv = await startServer();
    const employee = pyEnv["hr.employee"].create({
        user_id: serverState.userId,
        work_contact_id: serverState.partnerId,
        leave_datetime_to: serializeDateTime(DateTime.now().plus({ days: 15 })),
    });
    pyEnv["res.users"].write([serverState.userId], {
        employee_ids: [(6, 0, employee)],
    });
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
    await contains(".o_avatar_card span", { text: "Back on Jan 4, 2025" });
});

test("Discuss Sidebar shows out of office indication", async () => {
    mockDate("2025-04-08 12:00:00");
    const pyEnv = await startServer();
    pyEnv["hr.employee"].create({
        user_id: serverState.userId,
        leave_datetime_to: serializeDateTime(DateTime.now().plus({ days: 3 })),
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-NotificationItem .text-warning", { text: "Back on Apr 11" });
});

test("Show 'back at' when back later today", async () => {
    mockDate("2025-04-08 09:00:00");
    mockTimeZone(0);
    const pyEnv = await startServer();
    pyEnv["hr.employee"].create({
        user_id: serverState.userId,
        leave_datetime_to: "2025-04-08 13:00:00",
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-NotificationItem .text-warning", { text: "Back at 1:00 PM" });
});

test("Show 'back on' when back on the afternoon of another day", async () => {
    mockDate("2025-04-08 09:00:00");
    mockTimeZone(0);
    const pyEnv = await startServer();
    pyEnv["hr.employee"].create({
        user_id: serverState.userId,
        leave_datetime_to: "2025-04-09 13:00:00",
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-NotificationItem .text-warning", { text: "Back on Apr 9" });
});

test("Show 'back on' with the day of the viewer", async () => {
    mockDate("2025-04-08 12:00:00", 9);
    const pyEnv = await startServer();
    // Back on Apr 9 at 8:00 AM for the viewer, still Apr 8 in UTC.
    pyEnv["hr.employee"].create({
        user_id: serverState.userId,
        leave_datetime_to: "2025-04-08 23:00:00",
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-NotificationItem .text-warning", { text: "Back on Apr 9" });
});

test("Show 'back at' once the day of the return comes", async () => {
    mockDate("2025-04-08 23:59:00", 0);
    const pyEnv = await startServer();
    pyEnv["hr.employee"].create({
        user_id: serverState.userId,
        leave_datetime_to: "2025-04-09 13:00:00",
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-NotificationItem .text-warning", { text: "Back on Apr 9" });
    await advanceTime(2 * 60 * 1000); // past midnight
    await contains(".o-mail-NotificationItem .text-warning", { text: "Back at 1:00 PM" });
});

test("Stop showing 'back at' once the return time has passed", async () => {
    mockDate("2025-04-08 12:58:00", 0);
    const pyEnv = await startServer();
    pyEnv["hr.employee"].create({
        user_id: serverState.userId,
        leave_datetime_to: "2025-04-08 13:00:00",
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-NotificationItem .text-warning", { text: "Back at 1:00 PM" });
    await contains(".o-mail-DiscussContent-header .o-mail-ImStatus[data-icon='travel']");
    await advanceTime(3 * 60 * 1000); // past the return time
    // nothing is displayed after the name of the correspondent anymore
    await contains(".o-mail-NotificationItem-line + .align-items-start:empty");
    await contains(".o-mail-DiscussContent-header .o-mail-ImStatus[data-icon='travel']", {
        count: 0,
    });
});

test("Show nothing when the return was on a previous day", async () => {
    mockDate("2025-04-09 09:00:00", 0);
    const pyEnv = await startServer();
    pyEnv["hr.employee"].create({
        user_id: serverState.userId,
        leave_datetime_to: "2025-04-08 13:00:00",
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-NotificationItem-line + .align-items-start:empty");
    await contains(".o-mail-DiscussContent-header .o-mail-ImStatus");
    await contains(".o-mail-DiscussContent-header .o-mail-ImStatus[data-icon='travel']", {
        count: 0,
    });
});

test("CTRL+K command shows out of office indication", async () => {
    mockDate("2025-04-08 12:00:00");
    const pyEnv = await startServer();
    pyEnv["hr.employee"].create({
        user_id: serverState.userId,
        leave_datetime_to: serializeDateTime(DateTime.now().plus({ days: 3 })),
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Discuss[data-active]");
    await press(["ctrl", "k"]);
    await contains(".o-mail-DiscussCommand .text-warning", {
        text: "Back on Apr 11",
    });
});
