import {
    click,
    contains,
    defineMailModels,
    insertText,
    onRpcBefore,
    openFormView,
    registerArchs,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { Deferred, tick } from "@odoo/hoot-mock";
import { asyncStep, mockService, waitForSteps } from "@web/../tests/web_test_helpers";

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

test("Show 'Followers only' placeholder for recipients input when no recipient", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "test name 1", email: "test1@odoo.com" });
    await start();
    await openFormView("res.partner", partnerId);
    await click("button", { text: "Send message" });
    await contains(".o-mail-RecipientsInput .o-autocomplete--input[placeholder='Followers only']");
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
            asyncStep("do-action");
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
    await contains(".o-mail-RecipientsInput .o_tag_badge_text:contains(John Jane)");
    await contains(".o-mail-RecipientsInput .o_tag_badge_text:contains(john@test.be)");
    await click("button[title='Open Full Composer']");
    await def;
    await waitForSteps(["do-action"]);
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
            asyncStep("do-action");
            expect(action.name).toBe("Log note");
            expect(action.context.default_subtype_xmlid).toBe("mail.mt_note");
            expect(action.context.default_partner_ids).toBeEmpty();
            def.resolve();
        },
    });
    await start();
    await openFormView("res.fake", fakeId);
    await click("button", { text: "Send message" });
    await contains(".o-mail-RecipientsInput .o_tag_badge_text:contains(John Jane)");
    await contains(".o-mail-RecipientsInput .o_tag_badge_text:contains(john@test.be)");
    await click("button", { text: "Log note" });
    await click("button[title='Open Full Composer']");
    await def;
    await waitForSteps(["do-action"]);
});

test("Check that a partner is created for new followers when sending a message", async () => {
    const pyEnv = await startServer();
    const [partnerId, partnerId_2] = pyEnv["res.partner"].create([
        { name: "John Jane", email: "john@jane.be" },
        { name: "Peter Johnson", email: "peter@johnson.be" },
    ]);
    const fakeId = pyEnv["res.fake"].create({
        email_cc: "john@test.be",
        partner_ids: [partnerId],
    });
    pyEnv["mail.followers"].create({
        partner_id: partnerId_2,
        email: "peter@johnson.be",
        is_active: true,
        res_id: fakeId,
        res_model: "res.fake",
    });
    registerArchs(archs);
    await start();
    await openFormView("res.fake", fakeId);
    await contains(".o-mail-Followers-counter", { text: "1" });
    await click("button", { text: "Send message" });
    await contains(".o-mail-RecipientsInput .o_tag_badge_text:contains(John Jane)");
    await contains(".o-mail-RecipientsInput .o_tag_badge_text:contains(john@test.be)");
    // Ensure that partner `john@test.be` is created while sending the message (not before)
    const partners = pyEnv["res.partner"].search_read([["email", "=", "john@test.be"]]);
    expect(partners).toHaveLength(0);
    await insertText(".o-mail-Composer-input", "Dummy Message");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Followers-counter", { text: "1" });
});

test("suggest recipient on 'Send message' composer", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Peter Johnson",
        email: "peter@johnson.be",
    });
    const fakeId = pyEnv["res.fake"].create({ email_cc: "john@test.be" });
    pyEnv["mail.followers"].create({
        partner_id: partnerId,
        email: "peter@johnson.be",
        is_active: true,
        res_id: fakeId,
        res_model: "res.fake",
    });
    registerArchs(archs);
    await start();
    await openFormView("res.fake", fakeId);
    await contains(".o-mail-Followers-counter", { text: "1" });
    await click("button", { text: "Send message" });
    await contains(".o-mail-RecipientsInput .o_tag_badge_text:contains(john@test.be)");
    // Ensure that partner `john@test.be` is created before sending the message
    expect(pyEnv["res.partner"].search_read([["email", "=", "john@test.be"]])).toHaveLength(0);
    await insertText(".o-mail-Composer-input", "Dummy Message");
    await click(".o-mail-Composer-send:enabled");
    await tick();
    expect(pyEnv["res.partner"].search_read([["email", "=", "john@test.be"]])).toHaveLength(1);
    await contains(".o-mail-Followers-counter", { text: "1" });
});

test("suggested recipients should not be notified when posting an internal note", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "John Jane",
        email: "john@jane.be",
    });
    const fakeId = pyEnv["res.fake"].create({ partner_ids: [partnerId] });
    onRpcBefore("/mail/message/post", (args) => {
        asyncStep("message_post");
        expect(args.post_data.partner_ids).toBeEmpty();
    });
    await start();
    await openFormView("res.fake", fakeId);
    await click("button", { text: "Log note" });
    await insertText(".o-mail-Composer-input", "Dummy Message");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message");
    await waitForSteps(["message_post"]);
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
    await contains(".o-mail-RecipientsInput .o_tag_badge_text", { text: "Test Partner, Invoice" });
});

test("update email for the partner on the fly", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "John Jane",
    });
    const fakeId = pyEnv["res.fake"].create({ partner_ids: [partnerId] });
    registerArchs(archs);
    await start();
    await openFormView("res.fake", fakeId);
    await click("button", { text: "Send message" });
    await insertText(".o-mail-RecipientsInputTagsListPopover input", "john@jane.be");
    await click(".o-mail-RecipientsInputTagsListPopover .btn-primary");

    await insertText(".o-mail-Composer-input", "Dummy Message");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message");
    await contains(".o-mail-Followers-counter", { text: "0" });
});

test("suggested recipients should not be added as follower when posting a message", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "John Jane",
        email: "john@jane.be",
    });
    const fakeId = pyEnv["res.fake"].create({ partner_ids: [partnerId] });
    registerArchs(archs);
    await start();
    await openFormView("res.fake", fakeId);
    await contains(".o-mail-Followers-counter", { text: "0" });
    await click("button", { text: "Send message" });
    await insertText(".o-mail-Composer-input", "Dummy Message");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message");
    await contains(".o-mail-Followers-counter", { text: "0" });
});
