/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { patchUiSize, SIZES } from "@mail/../tests/helpers/patch_ui_size";
import { start } from "@mail/../tests/helpers/test_utils";

import { getFixture } from "@web/../tests/helpers/utils";
import { click, contains, insertText, scroll } from "@web/../tests/utils";

QUnit.module("chatter (patch)", {
    beforeEach() {
        patchUiSize({ size: SIZES.XXL });
    },
});

QUnit.test("Message list loads new messages on scroll", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        display_name: "Partner 11",
        description: [...Array(61).keys()].join("\n"),
    });
    for (let i = 0; i < 60; i++) {
        pyEnv["mail.message"].create({
            body: "<p>not empty</p>",
            model: "res.partner",
            res_id: partnerId,
        });
    }
    const views = {
        "res.partner,false,form": `
            <form string="Partners">
                <sheet>
                    <field name="name"/>
                    <field name="description"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_ids"/>
                </div>
            </form>`,
    };
    const target = getFixture();
    target.classList.add("o_web_client");
    const { openFormView } = await start({
        serverData: { views },
        target,
    });
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Message", { count: 30 });
    await scroll(".o-mail-Chatter", "bottom");
    await contains(".o-mail-Message", { count: 60 });
});

QUnit.test("Message list is scrolled to new message after posting a message", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        activity_ids: [],
        display_name: "<p>Partner 11</p>",
        description: [...Array(60).keys()].join("\n"),
        message_ids: [],
        message_follower_ids: [],
    });
    for (let i = 0; i < 60; i++) {
        pyEnv["mail.message"].create({
            body: "<p>not empty</p>",
            model: "res.partner",
            res_id: partnerId,
        });
    }
    const views = {
        "res.partner,false,form": `
            <form string="Partners">
                <header>
                    <button name="primaryButton" string="Primary" type="object" class="oe_highlight"/>
                </header>
                <sheet>
                    <field name="name"/>
                    <field name="description"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_ids" options="{'post_refresh': 'always'}"/>
                </div>
            </form>`,
    };
    const target = getFixture();
    target.classList.add("o_web_client");
    const { openFormView } = await start({
        serverData: { views },
        target,
    });
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Message", { count: 30 });
    await contains(".o-mail-Form-chatter.o-aside");
    await contains(".o_content", { scroll: 0 });
    await contains(".o-mail-Chatter", { scroll: 0 });
    await scroll(".o-mail-Chatter", "bottom");
    await contains(".o-mail-Message", { count: 60 });
    await contains(".o_content", { scroll: 0 });
    await click("button", { text: "Log note" });
    await insertText(".o-mail-Composer-input", "New Message");
    await click(".o-mail-Composer-send:not(:disabled)");
    await contains(".o-mail-Composer-input", { count: 0 });
    await contains(".o-mail-Message", { count: 61 });
    await contains(".o-mail-Message-content", { text: "New Message" });
    await contains(".o_content", { scroll: 0 });
    await contains(".o-mail-Chatter", { scroll: 0 });
});
