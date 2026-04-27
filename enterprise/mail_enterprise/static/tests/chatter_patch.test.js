import {
    click,
    contains,
    defineMailModels,
    insertText,
    openFormView,
    patchUiSize,
    registerArchs,
    scroll,
    SIZES,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { beforeEach, describe, test } from "@odoo/hoot";

describe.current.tags("desktop");
defineMailModels();
beforeEach(() => patchUiSize({ size: SIZES.XXL }));

test("Message list loads new messages on scroll", async () => {
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
    registerArchs({
        "res.partner,false,form": `
            <form string="Partners">
                <sheet>
                    <field name="name"/>
                    <field name="description"/>
                </sheet>
                <chatter/>
            </form>`,
    });

    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Message", { count: 30 });
    await scroll(".o-mail-Chatter", "bottom");
    await contains(".o-mail-Message", { count: 60 });
});

test("Message list is scrolled to new message after posting a message", async () => {
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
    registerArchs({
        "res.partner,false,form": `
            <form string="Partners">
                <header>
                    <button name="primaryButton" string="Primary" type="object" class="oe_highlight"/>
                </header>
                <sheet>
                    <field name="name"/>
                    <field name="description"/>
                </sheet>
                <chatter reload_on_post="True" reload_on_attachment="True"/>
            </form>`,
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Message", { count: 30 });
    await contains(".o-mail-Form-chatter.o-aside");
    await scroll(".o_content", 0);
    await scroll(".o-mail-Chatter", 0);
    await scroll(".o-mail-Chatter", "bottom");
    await contains(".o-mail-Message", { count: 60 });
    await scroll(".o_content", 0);
    await click("button", { text: "Log note" });
    await insertText(".o-mail-Composer-input", "New Message");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Composer-input", { count: 0 });
    await contains(".o-mail-Message", { count: 61 });
    await contains(".o-mail-Message-content", { text: "New Message" });
    await scroll(".o_content", 0);
    await scroll(".o-mail-Chatter", 0);
});
