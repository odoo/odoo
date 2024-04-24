import {
    click,
    contains,
    defineMailModels,
    openFormView,
    start,
    startServer,
    triggerEvents,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("base rendering not editable", async () => {
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await contains(".o-mail-Chatter-follow", { text: "Follow" });
});

test("hover following button", async () => {
    const pyEnv = await startServer();
    const threadId = pyEnv["res.partner"].create({});
    pyEnv["mail.followers"].create({
        is_active: true,
        partner_id: serverState.partnerId,
        res_id: threadId,
        res_model: "res.partner",
    });
    await start();
    await openFormView("res.partner", threadId);
    await contains(".o-mail-Chatter-follow", { text: "Following" });
    await triggerEvents(".o-mail-Chatter-follow", ["mouseenter"], { text: "Following" });
    await contains(".o-mail-Chatter-follow", { text: "Unfollow" });
});

test('click on "follow" button', async () => {
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await contains("button", { text: "Follow" });
    await click("button", { text: "Follow" });
    await contains("button", { text: "Following" });
});

test('Click on "follow" button should save draft record', async () => {
    await start();
    await openFormView("res.partner", undefined, {
        arch: `
            <form string="Partners">
                <sheet>
                    <field name="name" required="1"/>
                </sheet>
                <chatter/>
            </form>`,
    });
    await contains("button", { text: "Follow" });
    await contains("div.o_field_char");
    await click("button", { text: "Follow" });
    await contains("div.o_field_invalid");
});

test('click on "unfollow" button', async () => {
    const pyEnv = await startServer();
    const threadId = pyEnv["res.partner"].create({});
    pyEnv["mail.followers"].create({
        is_active: true,
        partner_id: serverState.partnerId,
        res_id: threadId,
        res_model: "res.partner",
    });
    await start();
    await openFormView("res.partner", threadId);
    await click(".o-mail-Chatter-follow", { text: "Following" });
    await contains("button", { text: "Follow" });
});
