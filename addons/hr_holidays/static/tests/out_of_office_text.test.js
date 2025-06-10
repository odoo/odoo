import { describe, test } from "@odoo/hoot";

import {
    startServer,
    start,
    click,
    openFormView,
    contains,
    openDiscuss,
    insertText,
    runComposerTests,
} from "@mail/../tests/mail_test_helpers";

import { defineHrHolidaysModels } from "@hr_holidays/../tests/hr_holidays_test_helpers";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { mockDate } from "@odoo/hoot-mock";

describe.current.tags("desktop");
defineHrHolidaysModels();

const { DateTime } = luxon;

test("Show 'back on' in avatar card", async () => {
    mockDate("2025-04-08 12:00:00");
    const pyEnv = await startServer();
    pyEnv["res.partner"].write([serverState.partnerId], {
        leave_date_to: DateTime.now().plus({ days: 3 }).toISODate(),
    });
    pyEnv["res.users"].write([serverState.userId], {
        leave_date_to: DateTime.now().plus({ days: 3 }).toISODate(),
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

runComposerTests([
    {
        title: "Show 'back on' in mention list",
        fn: async ({ useHtmlComposer }) => {
            mockDate("2025-04-08 12:00:00");
            const pyEnv = await startServer();
            pyEnv["res.partner"].write([serverState.partnerId], {
                leave_date_to: DateTime.now().plus({ days: 3 }).toISODate(),
            });
            pyEnv["res.users"].write([serverState.userId], {
                leave_date_to: DateTime.now().plus({ days: 3 }).toISODate(),
            });
            const channelId = pyEnv["discuss.channel"].create({
                name: "General & good",
                channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
            });
            await start({ useHtmlComposer });
            await openDiscuss(channelId);
            await insertText(".o-mail-Composer-input", "@");
            if (useHtmlComposer) {
                await contains(".o-mail-Composer-suggestion", { text: "Back on Apr 11" });
            } else {
                await contains(".o-mail-NavigableList-item span", { text: "Back on Apr 11" });
            }
        },
    },
]);

test("Show year when 'back on' is on different year than now", async () => {
    mockDate("2024-12-20 12:00:00");
    const pyEnv = await startServer();
    pyEnv["res.partner"].write([serverState.partnerId], {
        leave_date_to: DateTime.now().plus({ days: 15 }).toISODate(),
    });
    pyEnv["res.users"].write([serverState.userId], {
        leave_date_to: DateTime.now().plus({ days: 15 }).toISODate(),
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
