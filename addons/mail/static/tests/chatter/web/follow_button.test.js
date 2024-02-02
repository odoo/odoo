/** @odoo-module */

import { test } from "@odoo/hoot";
import {
    click,
    contains,
    openFormView,
    registerArchs,
    start,
    startServer,
    triggerEvents,
} from "../../mail_test_helpers";
import { constants } from "@web/../tests/web_test_helpers";

test.skip("base rendering not editable", async () => {
    await start();
    await openFormView("res.partner", constants.PARTNER_ID);
    await contains(".o-mail-Chatter-follow", { text: "Follow" });
});

test.skip("hover following button", async () => {
    const pyEnv = await startServer();
    const threadId = pyEnv["res.partner"].create({});
    pyEnv["mail.followers"].create({
        is_active: true,
        partner_id: constants.PARTNER_ID,
        res_id: threadId,
        res_model: "res.partner",
    });
    await start();
    await openFormView("res.partner", threadId);
    await contains(".o-mail-Chatter-follow", { text: "Following" });
    await triggerEvents(".o-mail-Chatter-follow", ["mouseenter"], { text: "Following" });
    await contains(".o-mail-Chatter-follow", { text: "Unfollow" });
});

test.skip('click on "follow" button', async () => {
    await start();
    await openFormView("res.partner", constants.PARTNER_ID);
    await contains("button", { text: "Follow" });
    await click("button", { text: "Follow" });
    await contains("button", { text: "Following" });
});

test.skip('Click on "follow" button should save draft record', async () => {
    registerArchs({
        "res.partner,false,form": `
            <form string="Partners">
                <sheet>
                    <field name="name" required="1"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_follower_ids"/>
                </div>
            </form>`,
    });
    await start();
    await openFormView("res.partner");
    await contains("button", { text: "Follow" });
    await contains("div.o_field_char");
    await click("button", { text: "Follow" });
    await contains("div.o_field_invalid");
});

test.skip('click on "unfollow" button', async () => {
    const pyEnv = await startServer();
    const threadId = pyEnv["res.partner"].create({});
    pyEnv["mail.followers"].create({
        is_active: true,
        partner_id: constants.PARTNER_ID,
        res_id: threadId,
        res_model: "res.partner",
    });
    await start();
    await openFormView("res.partner", threadId);
    await click(".o-mail-Chatter-follow", { text: "Following" });
    await contains("button", { text: "Follow" });
});
