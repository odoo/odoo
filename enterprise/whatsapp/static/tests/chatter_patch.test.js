import { describe, test } from "@odoo/hoot";
import {
    click,
    contains,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { serverState } from "@web/../tests/web_test_helpers";
import { defineWhatsAppModels } from "@whatsapp/../tests/whatsapp_test_helpers";

describe.current.tags("desktop");
defineWhatsAppModels();

test("WhatsApp template message composer dialog should be open after clicking on whatsapp button", async () => {
    const pyEnv = await startServer();
    pyEnv["whatsapp.template"].create({
        name: "WhatsApp Template 1",
        status: "approved",
    });
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await click("button", { text: "WhatsApp" });
    await contains(".o_dialog h4", { text: "Send WhatsApp Message" });
});
