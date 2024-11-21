import {
    click,
    contains,
    defineMailModels,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";

import { describe, test } from "@odoo/hoot";

describe.current.tags("desktop");
defineMailModels();

test("following internal link from chatter does not open chat window", async function () {
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
    /**
     * Asserting 0 chat window at this step is not sufficient because it doesn't give enough time
     * for the potential unwanted chat window to open. Opening another chat window and making sure
     * only 1 is present at the end (rather than 2) makes the test more robust.
     */
    await contains(".o-mail-ChatWindow", { count: 0 });
    await click(".o_menu_systray i[aria-label='Messages']");
    await click("button", { text: "New Message" });
    await contains(".o-mail-ChatWindow-header", { text: "New message" });
    await contains(".o-mail-ChatWindow", { count: 1 });
});
