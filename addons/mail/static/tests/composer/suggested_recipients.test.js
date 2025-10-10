import {
    assertSteps,
    click,
    contains,
    defineMailModels,
    insertText,
    onRpcBefore,
    openFormView,
    registerArchs,
    start,
    startServer,
    step,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { Deferred, tick } from "@odoo/hoot-mock";
import { mockService } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

const archs = {
    "res.fake,false,form": `
        <form string="Fake">
            <sheet></sheet>
            <chatter/>
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

test("with 3 or less suggested recipients: no 'show more' button", async () => {
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

test("Opening full composer in 'send message' mode should copy selected suggested recipients", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "John Jane",
        email: "john@jane.be",
    });
    const fakeId = pyEnv["res.fake"].create({
        email_cc: "john@test.be",
        phone: "123456789",
        partner_ids: [partnerId],
    });
    const def = new Deferred();
    mockService("action", {
        async doAction(action) {
            if (action?.res_model === "res.fake") {
                return super.doAction(...arguments);
            }
            step("do-action");
            expect(action.name).toBe("Compose Email");
            expect(action.context.default_subtype_xmlid).toBe("mail.mt_comment");
            expect(action.context.default_partner_ids).toHaveLength(2);
            const [johnTestPartnerId] = pyEnv["res.partner"].search([
                ["email", "=", "john@test.be"],
            ]);
            expect(action.context.default_partner_ids).toEqual([johnTestPartnerId, partnerId]);
            def.resolve();
        },
    });
    await start();
    await openFormView("res.fake", fakeId);
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
    await assertSteps(["do-action"]);
});

test("Opening full composer in 'log note' mode should not copy selected suggested recipients", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "John Jane",
        email: "john@jane.be",
    });
    const fakeId = pyEnv["res.fake"].create({
        email_cc: "john@test.be",
        partner_ids: [partnerId],
    });
    const def = new Deferred();
    mockService("action", {
        async doAction(action) {
            if (action?.res_model === "res.fake") {
                return super.doAction(...arguments);
            }
            step("do-action");
            expect(action.name).toBe("Log note");
            expect(action.context.default_subtype_xmlid).toBe("mail.mt_note");
            expect(action.context.default_partner_ids).toBeEmpty();
            def.resolve();
        },
    });
    await start();
    await openFormView("res.fake", fakeId);
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
    await assertSteps(["do-action"]);
});

test("more than 3 suggested recipients: display only 3 and 'show more' button", async () => {
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

test("more than 3 suggested recipients: show all of them on click 'show more' button", async () => {
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

test("more than 3 suggested recipients -> click 'show more' -> 'show less' button", async () => {
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

test("suggested recipients list display 3 suggested recipient and 'show more' button when 'show less' button is clicked", async () => {
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

test("suggest recipient on 'Send message' composer (all checked by default)", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "John Jane",
        email: "john@jane.be",
    });
    const fakeId = pyEnv["res.fake"].create({
        email_cc: "john@test.be",
        partner_ids: [partnerId],
    });
    registerArchs(archs);
    await start();
    await openFormView("res.fake", fakeId);
    await click("button", { text: "Send message" });
    await contains(".o-mail-SuggestedRecipient input:checked", { count: 2 });
    expect(
        ".o-mail-SuggestedRecipient:not([data-partner-id]) input[type=checkbox]:first"
    ).toBeChecked();
    expect(
        `.o-mail-SuggestedRecipient[data-partner-id="${partnerId}"] input[type=checkbox]:first`
    ).toBeChecked();
    // Ensure that partner `john@test.be` is created while sending the message (not before)
    let partners = pyEnv["res.partner"].search_read([["email", "=", "john@test.be"]]);
    expect(partners).toHaveLength(0);
    await insertText(".o-mail-Composer-input", "Dummy Message");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Followers-counter", { text: "2" });
    partners = pyEnv["res.partner"].search_read([["email", "=", "john@test.be"]]);
    expect(partners).toHaveLength(1);
});

test("suggest recipient on 'Send message' composer (recipient checked/unchecked)", async () => {
    const pyEnv = await startServer();
    const fakeId = pyEnv["res.fake"].create({ email_cc: "john@test.be" });
    registerArchs(archs);
    await start();
    await openFormView("res.fake", fakeId);
    await click("button", { text: "Send message" });
    await contains(".o-mail-SuggestedRecipient input:checked", { count: 1 });
    expect(
        ".o-mail-SuggestedRecipient:not([data-partner-id]) input[type=checkbox]:first"
    ).toBeChecked();
    // Ensure that partner `john@test.be` is created before sending the message
    await click(".o-mail-SuggestedRecipient input");
    await click(".o-mail-SuggestedRecipient input");
    await click(".o_dialog .o_form_button_save");
    await tick();
    const partners = pyEnv["res.partner"].search_read([["email", "=", "john@test.be"]]);
    expect(partners).toHaveLength(1);
    await insertText(".o-mail-Composer-input", "Dummy Message");
    await click(".o-mail-Composer-send:enabled");
    await tick();
    await contains(".o-mail-Followers-counter", { text: "1" });
});

test("display reason for suggested recipient on mouse over", async () => {
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

test("suggested recipients should not be notified when posting an internal note", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        display_name: "John Jane",
        email: "john@jane.be",
    });
    const fakeId = pyEnv["res.fake"].create({ partner_ids: [partnerId] });
    onRpcBefore("/mail/message/post", (args) => {
        step("message_post");
        expect(args.post_data.partner_ids).toBeEmpty();
    });
    await start();
    await openFormView("res.fake", fakeId);
    await click("button", { text: "Log note" });
    await insertText(".o-mail-Composer-input", "Dummy Message");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message");
    await assertSteps(["message_post"]);
});

test("suggested recipients should be added as follower when posting a message", async () => {
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

test("suggested recipients without name should show display_name instead", async () => {
    const pyEnv = await startServer();
    const [partner1, partner2] = pyEnv["res.partner"].create([
        { name: "Test Partner" },
        // Partner without name
        { type: "invoice" },
    ]);

    pyEnv["res.partner"].write([partner2], { parent_id: partner1 });
    const fakeId = pyEnv["res.fake"].create({ partner_ids: [partner2] });
    registerArchs(archs);
    await start();
    await openFormView("res.fake", fakeId);
    await click("button", { text: "Send message" });
    await contains(".o-mail-SuggestedRecipient", {
        text: "Test Partner, Invoice Address",
        contains: ["input[type=checkbox]:checked"],
    });
});
