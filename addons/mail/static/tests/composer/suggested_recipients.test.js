/** @odoo-module */

import { expect, test } from "@odoo/hoot";
import {
    click,
    contains,
    insertText,
    openFormView,
    registerArchs,
    start,
    startServer,
} from "../mail_test_helpers";
import { onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { Deferred, tick } from "@odoo/hoot-mock";
import { MailThread } from "../mock_server/mock_models/mail_thread";

const archs = {
    "res.fake,false,form": `
        <form string="Fake">
            <sheet></sheet>
            <div class="oe_chatter">
                <field name="message_ids"/>
                <field name="message_follower_ids"/>
            </div>
        </form>`,
    "res.partner,false,form": `
        <form string="Partner">
            <sheet>
                <field name="name"/>
                <field name="email"/>
                <field name="phone"/>
            </sheet>
        </form>`,
};

test.skip("with 3 or less suggested recipients: no 'show more' button", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        display_name: "John Jane",
        email: "john@jane.be",
    });
    const fakeId = pyEnv["res.fake"].create({
        email_cc: "john@test.be",
        partner_ids: [partnerId],
    });
    await start();
    await openFormView("res.fake", fakeId);
    await click("button", { text: "Send message" });
    await contains(".o-mail-SuggestedRecipient", { count: 2 });
    await contains("button", { count: 0, text: "Show more" });
});

test.skip("Opening full composer in 'send message' mode should copy selected suggested recipients", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        display_name: "John Jane",
        email: "john@jane.be",
    });
    const fakeId = pyEnv["res.fake"].create({
        email_cc: "john@test.be",
        phone: "123456789",
        partner_ids: [partnerId],
    });
    const { env } = await start();
    await openFormView("res.fake", fakeId);
    const def = new Deferred();
    patchWithCleanup(env.services.action, {
        doAction(action) {
            expect.step("do-action");
            expect(action.name).toBe("Compose Email");
            expect(action.context.default_subtype_xmlid).toBe("mail.mt_comment");
            expect(action.context.default_partner_ids).toHaveCount(2);
            const johnTestPartnerId = pyEnv["res.partner"].search([
                ["email", "=", "john@test.be"],
                ["phone", "=", "123456789"],
            ])[0];
            expect(action.context.default_partner_ids).toEqual([johnTestPartnerId, partnerId]);
            def.resolve();
            return Promise.resolve();
        },
    });
    await click("button", { text: "Send message" });
    await contains(".o-mail-SuggestedRecipient", {
        text: "john@test.be",
        contains: ["input[type=checkbox]:checked"],
    });
    await contains(".o-mail-SuggestedRecipient", {
        text: "John Jane",
        contains: ["input[type=checkbox]:checked"],
    });
    await click("button[title='Full composer']");
    await def;
    expect(["do-action"]).toVerifySteps();
});

test.skip("Opening full composer in 'log note' mode should not copy selected suggested recipients", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        display_name: "John Jane",
        email: "john@jane.be",
    });
    const fakeId = pyEnv["res.fake"].create({
        email_cc: "john@test.be",
        partner_ids: [partnerId],
    });
    const { env } = await start();
    await openFormView("res.fake", fakeId);
    const def = new Deferred();
    patchWithCleanup(env.services.action, {
        doAction(action) {
            expect.step("do-action");
            expect(action.name).toBe("Log note");
            expect(action.context.default_subtype_xmlid).toBe("mail.mt_note");
            expect(action.context.default_partner_ids).toBeEmpty();
            def.resolve();
            return Promise.resolve();
        },
    });
    await click("button", { text: "Send message" });
    await contains(".o-mail-SuggestedRecipient", {
        text: "john@test.be",
        contains: ["input[type=checkbox]:checked"],
    });
    await contains(".o-mail-SuggestedRecipient", {
        text: "John Jane",
        contains: ["input[type=checkbox]:checked"],
    });
    await click("button", { text: "Log note" });
    await click("button[title='Full composer']");
    await def;
    expect(["do-action"]).toVerifySteps();
});

test.skip("more than 3 suggested recipients: display only 3 and 'show more' button", async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2, partnerId_3, partnerId_4] = pyEnv["res.partner"].create([
        { display_name: "John Jane", email: "john@jane.be" },
        { display_name: "Jack Jone", email: "jack@jone.be" },
        { display_name: "jack sparrow", email: "jsparrow@blackpearl.bb" },
        { display_name: "jolly Roger", email: "Roger@skullflag.com" },
    ]);
    const fakeId = pyEnv["res.fake"].create({
        partner_ids: [partnerId_1, partnerId_2, partnerId_3, partnerId_4],
    });
    registerArchs(archs);
    await start();
    await openFormView("res.fake", fakeId);
    await click("button", { text: "Send message" });
    await contains("button", { text: "Show more" });
});

test.skip("more than 3 suggested recipients: show all of them on click 'show more' button", async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2, partnerId_3, partnerId_4] = pyEnv["res.partner"].create([
        { display_name: "John Jane", email: "john@jane.be" },
        { display_name: "Jack Jone", email: "jack@jone.be" },
        { display_name: "jack sparrow", email: "jsparrow@blackpearl.bb" },
        { display_name: "jolly Roger", email: "Roger@skullflag.com" },
    ]);
    const fakeId = pyEnv["res.fake"].create({
        partner_ids: [partnerId_1, partnerId_2, partnerId_3, partnerId_4],
    });
    registerArchs(archs);
    await start();
    await openFormView("res.fake", fakeId);
    await click("button", { text: "Send message" });
    await click("button", { text: "Show more" });
    await contains(".o-mail-SuggestedRecipient", { count: 4 });
});

test.skip("more than 3 suggested recipients -> click 'show more' -> 'show less' button", async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2, partnerId_3, partnerId_4] = pyEnv["res.partner"].create([
        { display_name: "John Jane", email: "john@jane.be" },
        { display_name: "Jack Jone", email: "jack@jone.be" },
        { display_name: "jack sparrow", email: "jsparrow@blackpearl.bb" },
        { display_name: "jolly Roger", email: "Roger@skullflag.com" },
    ]);
    const fakeId = pyEnv["res.fake"].create({
        partner_ids: [partnerId_1, partnerId_2, partnerId_3, partnerId_4],
    });
    registerArchs(archs);
    await start();
    await openFormView("res.fake", fakeId);
    await click("button", { text: "Send message" });
    await click("button", { text: "Show more" });
    await contains("button", { text: "Show less" });
});

test.skip("suggested recipients list display 3 suggested recipient and 'show more' button when 'show less' button is clicked", async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2, partnerId_3, partnerId_4] = pyEnv["res.partner"].create([
        { display_name: "John Jane", email: "john@jane.be" },
        { display_name: "Jack Jone", email: "jack@jone.be" },
        { display_name: "jack sparrow", email: "jsparrow@blackpearl.bb" },
        { display_name: "jolly Roger", email: "Roger@skullflag.com" },
    ]);
    const fakeId = pyEnv["res.fake"].create({
        partner_ids: [partnerId_1, partnerId_2, partnerId_3, partnerId_4],
    });
    registerArchs(archs);
    await start();
    await openFormView("res.fake", fakeId);
    await click("button", { text: "Send message" });
    await click("button", { text: "Show more" });
    await click("button", { text: "Show less" });
    await contains(".o-mail-SuggestedRecipient", { count: 3 });
    await contains("button", { text: "Show more" });
});

test.skip("suggest recipient on 'Send message' composer (all checked by default)", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        display_name: "John Jane",
        email: "john@jane.be",
    });
    const fakeId = pyEnv["res.fake"].create({
        email_cc: "john@test.be",
        partner_ids: [partnerId],
        phone: "123456789",
    });
    registerArchs(archs);
    await start();
    await openFormView("res.fake", fakeId);
    await click("button", { text: "Send message" });
    await contains(".o-mail-SuggestedRecipient input:checked", { count: 2 });
    expect(
        $(".o-mail-SuggestedRecipient:not([data-partner-id]) input[type=checkbox]")[0]
    ).toBeChecked();
    expect(
        $(`.o-mail-SuggestedRecipient[data-partner-id="${partnerId}"] input[type=checkbox]`)[0]
    ).toBeChecked();
    // Ensure that partner `john@test.be` is created while sending the message (not before)
    let partners = pyEnv["res.partner"].search_read([
        ["email", "=", "john@test.be"],
        ["phone", "=", "123456789"],
    ]);
    expect(partners).toHaveCount(0);
    await insertText(".o-mail-Composer-input", "Dummy Message");
    await click(".o-mail-Composer-send");
    await tick();
    partners = pyEnv["res.partner"].search_read([
        ["email", "=", "john@test.be"],
        ["phone", "=", "123456789"],
    ]);
    expect(partners).toHaveCount(1);
    await contains(".o-mail-Followers-counter", { text: "2" });
});

test.skip("suggest recipient on 'Send message' composer (recipient checked/unchecked)", async () => {
    const pyEnv = await startServer();
    const fakeId = pyEnv["res.fake"].create({
        email_cc: "john@test.be",
        phone: "123456789",
    });
    registerArchs(archs);
    await start();
    await openFormView("res.fake", fakeId);
    await click("button", { text: "Send message" });
    await contains(".o-mail-SuggestedRecipient input:checked", { count: 1 });
    expect(
        $(".o-mail-SuggestedRecipient:not([data-partner-id]) input[type=checkbox]")[0]
    ).toBeChecked();
    // Ensure that partner `john@test.be` is created before sending the message
    await click(".o-mail-SuggestedRecipient input");
    await click(".o-mail-SuggestedRecipient input");
    await click(".o_dialog .o_form_button_save");
    await tick();
    const partners = pyEnv["res.partner"].search_read([
        ["email", "=", "john@test.be"],
        ["phone", "=", "123456789"],
    ]);
    expect(partners).toHaveCount(1);
    await insertText(".o-mail-Composer-input", "Dummy Message");
    await click(".o-mail-Composer-send");
    await tick();
    await contains(".o-mail-Followers-counter", { text: "1" });
});

test.skip("display reason for suggested recipient on mouse over", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        display_name: "John Jane",
        email: "john@jane.be",
    });
    const fakeId = pyEnv["res.fake"].create({ partner_ids: [partnerId] });
    registerArchs(archs);
    await start();
    await openFormView("res.fake", fakeId);
    await click("button", { text: "Send message" });
    await contains(
        `.o-mail-SuggestedRecipient[data-partner-id="${partnerId}"][title="Add as recipient and follower (reason: Email partner)"]`
    );
});

test.skip("suggested recipients should not be notified when posting an internal note", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        display_name: "John Jane",
        email: "john@jane.be",
    });
    const fakeId = pyEnv["res.fake"].create({ partner_ids: [partnerId] });
    onRpc((route, args) => {
        if (route === "/mail/message/post") {
            expect(args.post_data.partner_ids).toBeEmpty();
        }
    });
    await start();
    await openFormView("res.fake", fakeId);
    await click("button", { text: "Log note" });
    await insertText(".o-mail-Composer-input", "Dummy Message");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message");
});

test.skip("suggested recipients should be added as follower when posting a message", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        display_name: "John Jane",
        email: "john@jane.be",
    });
    const fakeId = pyEnv["res.fake"].create({ partner_ids: [partnerId] });
    registerArchs(archs);
    await start();
    await openFormView("res.fake", fakeId);
    await click("button", { text: "Send message" });
    await insertText(".o-mail-Composer-input", "Dummy Message");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message");
    await contains(".o-mail-Followers-counter", { text: "1" });
});

test.skip("suggested partner unchecked/checked -> partner creation in wizard with defaults", async () => {
    const pyEnv = await startServer();
    const fakeId = pyEnv["res.fake"].create({
        email_cc: "john@test.be",
    });
    let partners = pyEnv["res.partner"].search([["email", "=", "john@test.be"]]);
    expect(partners).toBeEmpty();
    patchWithCleanup(MailThread.prototype, {
        _get_mail_thread_data() {
            // Override mockRPC response to simulate retrieving default values
            // for the suggested recipient through `_get_customer_information`
            const res = super._get_mail_thread_data(...arguments);
            expect(res["suggestedRecipients"]).toHaveCount(1);
            expect(res["suggestedRecipients"][0][1]).toEqual("john@test.be");
            res["suggestedRecipients"][0].push({ company_name: "Test Company" });
            return res;
        },
    });
    registerArchs(archs);
    await start();
    await openFormView("res.fake", fakeId);
    await click("button", { text: "Send message" });
    await click(".o-mail-SuggestedRecipient input");
    await click(".o-mail-SuggestedRecipient input");
    await tick();
    await click(".o_dialog .o_form_button_save");
    await tick();
    partners = pyEnv["res.partner"].search([
        ["email", "=", "john@test.be"],
        ["company_name", "=", "Test Company"],
    ]);
    expect(partners).toHaveCount(1);
});
