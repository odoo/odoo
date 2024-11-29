import {
    click,
    contains,
    defineMailModels,
    insertText,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";

import { describe, test } from "@odoo/hoot";

describe.current.tags("desktop");
defineMailModels();

test("following internal link from chatter does not open chat window", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Jeanne" });
    pyEnv["mail.message"].create({
        body: `Created by <a href="#" data-oe-model="res.partner" data-oe-id="${pyEnv.user.partner_id}">Admin</a>`,
        model: "res.partner",
        res_id: partnerId,
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o_last_breadcrumb_item", { text: "Jeanne" });
    await click("a", { text: "Admin" });
    await contains(".o_last_breadcrumb_item", { text: "Mitchell Admin" });
    // Assert 0 chat windows not sufficient because not enough time for potential chat window opening.
    // Let's open another chat window to give some time and assert only manually open chat window opens.
    await contains(".o-mail-ChatWindow", { count: 0 });
    await click(".o_menu_systray i[aria-label='Messages']");
    await click("button", { text: "New Message" });
    await insertText("input[placeholder='Search a conversation']", "abc");
    await click("a", { text: "Create Channel" });
    await contains(".o-mail-ChatWindow-header", { text: "abc" });
    await contains(".o-mail-ChatWindow", { count: 1 });
});
