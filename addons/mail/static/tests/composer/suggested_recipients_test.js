/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { makeDeferred, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { click, contains, insertText } from "@web/../tests/utils";

const views = {
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

QUnit.module("suggested_recipients");

QUnit.test("with 3 or less suggested recipients: no 'show more' button", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        display_name: "John Jane",
        email: "john@jane.be",
    });
    const fakeId = pyEnv["res.fake"].create({
        email_cc: "john@test.be",
        partner_ids: [partnerId],
    });
    const { openFormView } = await start();
    openFormView("res.fake", fakeId);
    await click("button", { text: "Send message" });
    await contains(".o-mail-SuggestedRecipient", { count: 2 });
    await contains("button", { count: 0, text: "Show more" });
});

QUnit.test(
    "Opening full composer in 'send message' mode should copy selected suggested recipients",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({
            display_name: "John Jane",
            email: "john@jane.be",
        });
        const fakeId = pyEnv["res.fake"].create({
            email_cc: "john@test.be",
            partner_ids: [partnerId],
        });
        const { env, openFormView } = await start();
        openFormView("res.fake", fakeId);
        const def = makeDeferred();
        patchWithCleanup(env.services.action, {
            doAction(action) {
                assert.step("do-action");
                assert.strictEqual(action.name, "Compose Email");
                assert.strictEqual(action.context.default_subtype_xmlid, "mail.mt_comment");
                assert.strictEqual(action.context.default_partner_ids.length, 2);
                const johnTestPartnerId = pyEnv["res.partner"].search([
                    ["email", "=", "john@test.be"],
                ])[0];
                assert.deepEqual(action.context.default_partner_ids, [
                    johnTestPartnerId,
                    partnerId,
                ]);
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
        assert.verifySteps(["do-action"]);
    }
);

QUnit.test(
    "Opening full composer in 'log note' mode should not copy selected suggested recipients",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({
            display_name: "John Jane",
            email: "john@jane.be",
        });
        const fakeId = pyEnv["res.fake"].create({
            email_cc: "john@test.be",
            partner_ids: [partnerId],
        });
        const { env, openFormView } = await start();
        openFormView("res.fake", fakeId);
        const def = makeDeferred();
        patchWithCleanup(env.services.action, {
            doAction(action) {
                assert.step("do-action");
                assert.strictEqual(action.name, "Log note");
                assert.strictEqual(action.context.default_subtype_xmlid, "mail.mt_note");
                assert.deepEqual(action.context.default_partner_ids, []);
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
        assert.verifySteps(["do-action"]);
    }
);

QUnit.test("more than 3 suggested recipients: display only 3 and 'show more' button", async () => {
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
    const { openFormView } = await start({ serverData: { views } });
    openFormView("res.fake", fakeId);
    await click("button", { text: "Send message" });
    await contains("button", { text: "Show more" });
});

QUnit.test(
    "more than 3 suggested recipients: show all of them on click 'show more' button",
    async () => {
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
        const { openFormView } = await start({ serverData: { views } });
        openFormView("res.fake", fakeId);
        await click("button", { text: "Send message" });
        await click("button", { text: "Show more" });
        await contains(".o-mail-SuggestedRecipient", { count: 4 });
    }
);

QUnit.test(
    "more than 3 suggested recipients -> click 'show more' -> 'show less' button",
    async () => {
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
        const { openFormView } = await start({ serverData: { views } });
        openFormView("res.fake", fakeId);
        await click("button", { text: "Send message" });
        await click("button", { text: "Show more" });
        await contains("button", { text: "Show less" });
    }
);

QUnit.test(
    "suggested recipients list display 3 suggested recipient and 'show more' button when 'show less' button is clicked",
    async () => {
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
        const { openFormView } = await start({ serverData: { views } });
        openFormView("res.fake", fakeId);
        await click("button", { text: "Send message" });
        await click("button", { text: "Show more" });
        await click("button", { text: "Show less" });
        await contains(".o-mail-SuggestedRecipient", { count: 3 });
        await contains("button", { text: "Show more" });
    }
);

QUnit.test(
    "suggest recipient on 'Send message' composer (all checked by default)",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({
            display_name: "John Jane",
            email: "john@jane.be",
        });
        const fakeId = pyEnv["res.fake"].create({
            email_cc: "john@test.be",
            partner_ids: [partnerId],
        });
        const { openFormView } = await start({ serverData: { views } });
        openFormView("res.fake", fakeId);
        await click("button", { text: "Send message" });
        await contains(".o-mail-SuggestedRecipient input:checked", { count: 2 });
        assert.ok(
            $(".o-mail-SuggestedRecipient:not([data-partner-id]) input[type=checkbox]")[0].checked
        );
        assert.ok(
            $(`.o-mail-SuggestedRecipient[data-partner-id="${partnerId}"] input[type=checkbox]`)[0]
                .checked
        );
    }
);

QUnit.test("display reason for suggested recipient on mouse over", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        display_name: "John Jane",
        email: "john@jane.be",
    });
    const fakeId = pyEnv["res.fake"].create({ partner_ids: [partnerId] });
    const { openFormView } = await start({ serverData: { views } });
    openFormView("res.fake", fakeId);
    await click("button", { text: "Send message" });
    await contains(
        `.o-mail-SuggestedRecipient[data-partner-id="${partnerId}"][title="Add as recipient and follower (reason: Email partner)"]`
    );
});

QUnit.test(
    "suggested recipients should not be notified when posting an internal note",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({
            display_name: "John Jane",
            email: "john@jane.be",
        });
        const fakeId = pyEnv["res.fake"].create({ partner_ids: [partnerId] });
        const { openFormView } = await start({
            serverData: { views },
            async mockRPC(route, args) {
                if (route === "/mail/message/post") {
                    assert.strictEqual(args.post_data.partner_ids.length, 0);
                }
            },
        });
        openFormView("res.fake", fakeId);
        await click("button", { text: "Log note" });
        await insertText(".o-mail-Composer-input", "Dummy Message");
        await click(".o-mail-Composer-send:enabled");
        await contains(".o-mail-Message");
    }
);

QUnit.test("suggested recipients should be added as follower when posting a message", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        display_name: "John Jane",
        email: "john@jane.be",
    });
    const fakeId = pyEnv["res.fake"].create({ partner_ids: [partnerId] });
    const { openFormView } = await start({
        serverData: { views },
    });
    openFormView("res.fake", fakeId);
    await click("button", { text: "Send message" });
    await insertText(".o-mail-Composer-input", "Dummy Message");
    await click(".o-mail-Composer-send:enabled");
    await contains(".o-mail-Message");
    await contains(".o-mail-Followers-counter", { text: "1" });
});

QUnit.test(
    "suggested partner unchecked/checked -> partner creation in wizard with defaults",
    async (assert) => {
        const pyEnv = await startServer();
        const fakeId = pyEnv["res.fake"].create({
            email_cc: "john@test.be",
        });
        let partner = pyEnv["res.partner"].search([["email", "=", "john@test.be"]]);
        assert.strictEqual(partner.length, 0);
        const { openFormView } = await start({
            serverData: { views },
            async mockRPC(route, args, performRPC) {
                // Override mockRPC response to simulate retrieving default values
                // for the suggested recipient through `_get_customer_information`
                if (route === "/mail/thread/data") {
                    const res = await performRPC(route, args);
                    assert.strictEqual(res["suggestedRecipients"].length, 1);
                    assert.deepEqual(res["suggestedRecipients"][0][1], "john@test.be");
                    res["suggestedRecipients"][0].push({
                        company_name: "Test Company",
                    });
                    return res;
                }
            },
        });
        openFormView("res.fake", fakeId);
        await click("button", { text: "Send message" });
        await click(".o-mail-SuggestedRecipient input");
        await click(".o-mail-SuggestedRecipient input");
        await nextTick();
        await click(".o_dialog .o_form_button_save");
        await nextTick();
        partner = pyEnv["res.partner"].search([
            ["email", "=", "john@test.be"],
            ["company_name", "=", "Test Company"],
        ]);
        assert.strictEqual(partner.length, 1);
    }
);
