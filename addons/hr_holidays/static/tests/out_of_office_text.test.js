import { describe, test } from "@odoo/hoot";

import {
    startServer,
    start,
    click,
    openFormView,
    contains,
    openDiscuss,
    insertText,
} from "@mail/../tests/mail_test_helpers";

import { defineHrHolidaysModels } from "@hr_holidays/../tests/hr_holidays_test_helpers";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { press } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";
import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";

describe.current.tags("desktop");
defineHrHolidaysModels();

const { DateTime } = luxon;

test("Show 'back on' in avatar card", async () => {
    mockDate("2025-04-08 12:00:00");
    const pyEnv = await startServer();
    const employee = pyEnv["hr.employee"].create({
        user_id: serverState.userId,
        work_contact_id: serverState.partnerId,
        leave_date_to: serializeDate(DateTime.now().plus({ days: 3 })),
        leave_date_from: serializeDateTime(DateTime.now().minus({ days: 2 })),
        leave_request_date_from_period: "am",
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

test("Show 'back on' during the leave period", async () => {
    mockDate("2025-04-08 08:00:00");
    const pyEnv = await startServer();
    const employee = pyEnv["hr.employee"].create({
        user_id: serverState.userId,
        work_contact_id: serverState.partnerId,
        leave_date_from: serializeDateTime(DateTime.now().minus({ days: 2 })),
        leave_date_to: serializeDate(DateTime.now().plus({ days: 3 })),
        leave_request_date_from_period: "am",
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

test("Show 'back on' during the leave period of one day", async () => {
    mockDate("2025-04-08 08:00:00");
    const pyEnv = await startServer();
    const employee = pyEnv["hr.employee"].create({
        user_id: serverState.userId,
        work_contact_id: serverState.partnerId,
        leave_date_from: serializeDateTime(DateTime.now()),
        leave_date_to: serializeDate(DateTime.now().plus({ days: 1 })),
        leave_request_date_from_period: "am",
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
    await contains(".o_avatar_card span", { text: "Back on Apr 9" });
});

test("Show 'back on' in mention list", async () => {
    mockDate("2025-04-08 12:00:00");
    const pyEnv = await startServer();
    const employee = pyEnv["hr.employee"].create({
        user_id: serverState.userId,
        leave_date_from: serializeDateTime(DateTime.now().minus({ days: 2 })),
        leave_date_to: serializeDate(DateTime.now().plus({ days: 3 })),
        leave_request_date_from_period: "am",
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
    await insertText(".o-mail-Composer-input", "@");
    await contains(".o-mail-NavigableList-item span", { text: "Back on Apr 11" });
});

test("Show year when 'back on' is on different year than now", async () => {
    mockDate("2024-12-20 12:00:00");
    const pyEnv = await startServer();
    const employee = pyEnv["hr.employee"].create({
        user_id: serverState.userId,
        work_contact_id: serverState.partnerId,
        leave_date_from: serializeDateTime(DateTime.now().minus({ days: 2 })),
        leave_date_to: serializeDateTime(DateTime.now().plus({ days: 15 })),
        leave_request_date_from_period: "am",
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
        leave_date_from: serializeDateTime(DateTime.now().minus({ days: 2 })),
        leave_date_to: serializeDateTime(DateTime.now().plus({ days: 15 })),
        leave_request_date_from_period: "am",
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-NotificationItem .text-warning", { text: "Back on Apr 23" });
});

test("CTRL+K command shows out of office indication", async () => {
    mockDate("2025-04-08 12:00:00");
    const pyEnv = await startServer();
    pyEnv["hr.employee"].create({
        user_id: serverState.userId,
        leave_date_from: serializeDateTime(DateTime.now().minus({ days: 2 })),
        leave_date_to: serializeDate(DateTime.now().plus({ days: 3 })),
        leave_request_date_from_period: "am",
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

test("Show 'Out tomorrow' in avatar card", async () => {
    mockDate("2025-04-08 12:00:00");
    const pyEnv = await startServer();
    const leave_date_from = DateTime.now().plus({ days: 1 });
    const leave_date_to = leave_date_from.plus({ days: 2 });
    const employee = pyEnv["hr.employee"].create({
        user_id: serverState.userId,
        work_contact_id: serverState.partnerId,
        leave_date_from: serializeDateTime(leave_date_from),
        leave_date_to: serializeDate(leave_date_to),
        leave_request_date_from_period: "am",
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
    await contains(".o_avatar_card span", { text: "Out tomorrow" });
});

test("Show 'Out this afternoon' in avatar card", async () => {
    mockDate("2025-04-08 08:00:00");
    const pyEnv = await startServer();
    const leave_date_from = DateTime.now();
    const leave_date_to = leave_date_from;

    const employee = pyEnv["hr.employee"].create({
        user_id: serverState.userId,
        work_contact_id: serverState.partnerId,
        leave_date_from: serializeDateTime(leave_date_from),
        leave_date_to: serializeDate(leave_date_to),
        leave_request_date_from_period: "pm",
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
    const text = `Out after ${leave_date_from.toLocaleString(DateTime.TIME_SIMPLE)}`;
    await contains(".o_avatar_card span", { text });
});

test("Show 'Out this afternoon' in avatar card for time based leave", async () => {
    mockDate("2025-04-08 13:00:00");
    const pyEnv = await startServer();
    const leave_date_from = DateTime.now();
    const leave_date_to = leave_date_from;

    const employee = pyEnv["hr.employee"].create({
        user_id: serverState.userId,
        work_contact_id: serverState.partnerId,
        leave_date_from: serializeDateTime(leave_date_from),
        leave_date_to: serializeDate(leave_date_to),
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
    const text = `Out after ${leave_date_from.toLocaleString(DateTime.TIME_SIMPLE)}`;
    await contains(".o_avatar_card span", { text });
});

test("Show 'Out tomorrow morning' in avatar card", async () => {
    mockDate("2025-04-08 12:00:00");
    const pyEnv = await startServer();
    const leave_date_from = DateTime.now().plus({ days: 1 });
    const leave_date_to = leave_date_from.plus({ days: 2 });
    const employee = pyEnv["hr.employee"].create({
        user_id: serverState.userId,
        work_contact_id: serverState.partnerId,
        leave_date_from: serializeDateTime(leave_date_from),
        leave_date_to: serializeDate(leave_date_to),
        leave_request_duration: "am",
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
    await contains(".o_avatar_card span", { text: "Out tomorrow morning" });
});

test("Show 'Out tomorrow afternoon' in avatar card", async () => {
    mockDate("2025-04-08 12:00:00");
    const pyEnv = await startServer();
    const leave_date_from = DateTime.now().plus({ days: 1 });
    const leave_date_to = leave_date_from.plus({ days: 2 });
    const employee = pyEnv["hr.employee"].create({
        user_id: serverState.userId,
        work_contact_id: serverState.partnerId,
        leave_date_from: serializeDateTime(leave_date_from),
        leave_date_to: serializeDate(leave_date_to),
        leave_request_duration: "pm",
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
    await contains(".o_avatar_card span", { text: "Out tomorrow afternoon" });
});

test("Show 'Out tomorrow afternoon' in avatar card for a multi-day leave starting in the afternoon", async () => {
    mockDate("2025-04-08 12:00:00");
    const pyEnv = await startServer();
    const leave_date_from = DateTime.now().plus({ days: 1 });
    const leave_date_to = leave_date_from.plus({ days: 2 });
    const employee = pyEnv["hr.employee"].create({
        user_id: serverState.userId,
        work_contact_id: serverState.partnerId,
        leave_date_from: serializeDateTime(leave_date_from),
        leave_date_to: serializeDate(leave_date_to),
        // multi-day based leave: leave_request_duration is always "full", but
        // leave_request_date_from_period should still take priority to show the afternoon start
        leave_request_duration: "full",
        leave_request_date_from_period: "pm",
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
    await contains(".o_avatar_card span", { text: "Out tomorrow afternoon" });
});

test("Show 'Out from' in avatar card when the next working day is on leave", async () => {
    mockDate("2025-04-11 13:00:00");
    const pyEnv = await startServer();
    const leave_date_from = DateTime.now().plus({ days: 3 });
    const leave_date_to = leave_date_from.plus({ days: 2 });
    const next_working_day_on_leave = leave_date_from;
    const employeeId = pyEnv["hr.employee"].create({
        user_id: serverState.userId,
        work_contact_id: serverState.partnerId,
        leave_date_from: serializeDateTime(leave_date_from),
        leave_date_to: serializeDate(leave_date_to),
        next_working_day_on_leave: serializeDate(next_working_day_on_leave),
    });
    pyEnv["res.users"].write([serverState.userId], {
        employee_ids: [Command.link(employeeId)],
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
    await contains(".o_avatar_card span", { text: "Out from Apr 14" });
});

test("Show 'back on' next to the author name of a message", async () => {
    mockDate("2025-04-08 12:00:00");
    const pyEnv = await startServer();
    const employeeId = pyEnv["hr.employee"].create({
        user_id: serverState.userId,
        work_contact_id: serverState.partnerId,
        leave_date_from: serializeDateTime(DateTime.now().minus({ days: 2 })),
        leave_date_to: serializeDate(DateTime.now().plus({ days: 3 })),
        leave_request_date_from_period: "am",
    });
    pyEnv["res.users"].write([serverState.userId], {
        employee_ids: [Command.link(employeeId)],
    });
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
    });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "not empty",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message-header .text-warning", { text: "Back on Apr 11" });
});
