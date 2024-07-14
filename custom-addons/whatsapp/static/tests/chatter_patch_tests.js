/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains } from "@web/../tests/utils";

QUnit.module("chatter (patch)");

QUnit.test(
    "WhatsApp template message composer dialog should be open after clicking on whatsapp button",
    async () => {
        const pyEnv = await startServer();
        pyEnv["whatsapp.template"].create({
            name: "WhatsApp Template 1",
            model: "res.partner",
            status: "approved",
        });
        const { openFormView } = await start();
        await openFormView("res.partner", pyEnv.currentPartnerId);
        await click("button", { text: "WhatsApp" });
        await contains(".o_dialog h4", { text: "Send WhatsApp Message" });
    }
);
