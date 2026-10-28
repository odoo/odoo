import {
    click,
    openFormView,
    start,
    startServer
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { defineWebsiteSlidesModels } from "@website_slides/../tests/website_slides_test_helpers";

describe.current.tags("desktop");
defineWebsiteSlidesModels();

test("grant course access", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const channelId = pyEnv["slide.channel"].create({});
    pyEnv["mail.activity"].create({
        can_write: true,
        res_id: channelId,
        request_partner_id: partnerId,
        res_model: "slide.channel",
    });
    await start();
    await openFormView("slide.channel", channelId);
    await waitFor(".o-mail-Activity:count(1)");
    await click("button", { text: "Grant Access" });
});

test("refuse course access", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const channelId = pyEnv["slide.channel"].create({});
    pyEnv["mail.activity"].create({
        can_write: true,
        res_id: channelId,
        request_partner_id: partnerId,
        res_model: "slide.channel",
    });
    await start();
    await openFormView("slide.channel", channelId);
    await waitFor(".o-mail-Activity:count(1)");
    await click("button", { text: "Refuse Access" });
});
