/** @odoo-module **/

import {
    click,
    insertText,
    start,
    startServer,
    waitUntil,
} from "@mail/../tests/helpers/test_utils";
import { patchWithCleanup } from "@web/../tests/helpers/utils";

const views = {
    "res.fake,false,form": `
        <form string="Fake">
            <sheet></sheet>
            <div class="oe_chatter">
                <field name="message_ids"/>
                <field name="message_follower_ids"/>
            </div>
        </form>`,
};

QUnit.module("suggested_recipients");

QUnit.test("with 3 or less suggested recipients: no 'show more' button", async (assert) => {
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
    await openFormView("res.fake", fakeId);
    await click("button:contains(Send message)");
    assert.containsNone($, "button:contains(Show more)");
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
        await openFormView("res.fake", fakeId);
        patchWithCleanup(env.services.action, {
            doAction(action) {
                assert.step("do-action");
                assert.strictEqual(action.name, "Compose Email");
                assert.strictEqual(action.context.default_subtype_xmlid, "mail.mt_comment");
                assert.deepEqual(action.context.default_partner_ids, [partnerId]);
                return Promise.resolve();
            },
        });
        await click("button:contains(Send message)");
        assert.containsOnce($, ".o-mail-SuggestedRecipient:contains(john@test.be)");
        assert.containsOnce($, ".o-mail-SuggestedRecipient:contains(John Jane)");
        assert.notOk(
            $(".o-mail-SuggestedRecipient:contains(john@test.be) input[type=checkbox]")[0].checked
        );
        assert.ok(
            $(".o-mail-SuggestedRecipient:contains(John Jane) input[type=checkbox]")[0].checked
        );
        await click("button[title='Full composer']");
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
        await openFormView("res.fake", fakeId);
        patchWithCleanup(env.services.action, {
            doAction(action) {
                assert.step("do-action");
                assert.strictEqual(action.name, "Log note");
                assert.strictEqual(action.context.default_subtype_xmlid, "mail.mt_note");
                assert.deepEqual(action.context.default_partner_ids, []);
                return Promise.resolve();
            },
        });
        await click("button:contains(Send message)");
        assert.containsOnce($, ".o-mail-SuggestedRecipient:contains(john@test.be)");
        assert.containsOnce($, ".o-mail-SuggestedRecipient:contains(John Jane)");
        assert.notOk(
            $(".o-mail-SuggestedRecipient:contains(john@test.be) input[type=checkbox]")[0].checked
        );
        assert.ok(
            $(".o-mail-SuggestedRecipient:contains(John Jane) input[type=checkbox]")[0].checked
        );
        await click("button:contains(Log note)");
        await click("button[title='Full composer']");
        assert.verifySteps(["do-action"]);
    }
);

QUnit.test(
    "more than 3 suggested recipients: display only 3 and 'show more' button",
    async (assert) => {
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
        await openFormView("res.fake", fakeId);
        await click("button:contains(Send message)");
        assert.containsOnce($, "button:contains(Show more)");
    }
);

QUnit.test(
    "more than 3 suggested recipients: show all of them on click 'show more' button",
    async (assert) => {
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
        await openFormView("res.fake", fakeId);
        await click("button:contains(Send message)");
        await click("button:contains(Show more)");
        assert.containsN($, ".o-mail-SuggestedRecipient", 4);
    }
);

QUnit.test(
    "more than 3 suggested recipients -> click 'show more' -> 'show less' button",
    async (assert) => {
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
        await openFormView("res.fake", fakeId);
        await click("button:contains(Send message)");
        await click("button:contains(Show more)");
        assert.containsOnce($, "button:contains(Show less)");
    }
);

QUnit.test(
    "suggested recipients list display 3 suggested recipient and 'show more' button when 'show less' button is clicked",
    async (assert) => {
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
        await openFormView("res.fake", fakeId);
        await click("button:contains(Send message)");
        await click("button:contains(Show more)");
        await click("button:contains(Show less)");
        assert.containsN($, ".o-mail-SuggestedRecipient", 3);
        assert.containsOnce($, "button:contains(Show more)");
    }
);

QUnit.test("suggest recipient on 'Send message' composer", async (assert) => {
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
    await openFormView("res.fake", fakeId);
    await click("button:contains(Send message)");
    assert.containsOnce($, ".o-mail-SuggestedRecipient input:checked");
});

QUnit.test("display reason for suggested recipient on mouse over", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        display_name: "John Jane",
        email: "john@jane.be",
    });
    const fakeId = pyEnv["res.fake"].create({ partner_ids: [partnerId] });
    const { openFormView } = await start({ serverData: { views } });
    await openFormView("res.fake", fakeId);
    await click("button:contains(Send message)");
    const partnerTitle = $(
        `.o-mail-SuggestedRecipient[data-partner-id="${partnerId}"]`
    )[0].getAttribute("title");
    assert.strictEqual(partnerTitle, "Add as recipient and follower (reason: Email partner)");
});

QUnit.test("suggested recipient without partner are unchecked by default", async (assert) => {
    const pyEnv = await startServer();
    const fakeId = pyEnv["res.fake"].create({ email_cc: "john@test.be" });
    const { openFormView } = await start({ serverData: { views } });
    await openFormView("res.fake", fakeId);
    await click("button:contains(Send message)");
    const checkboxUnchecked = $(
        ".o-mail-SuggestedRecipient:not([data-partner-id]) input[type=checkbox]"
    )[0];
    assert.notOk(checkboxUnchecked.checked);
});

QUnit.test("suggested recipient with partner are checked by default", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        display_name: "John Jane",
        email: "john@jane.be",
    });
    const fakeId = pyEnv["res.fake"].create({ partner_ids: [partnerId] });
    const { openFormView } = await start({ serverData: { views } });
    await openFormView("res.fake", fakeId);
    await click("button:contains(Send message)");
    assert.ok(
        $(`.o-mail-SuggestedRecipient[data-partner-id="${partnerId}"] input[type=checkbox]`)[0]
            .checked
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
        await openFormView("res.fake", fakeId);
        await click("button:contains(Log note)");
        await insertText(".o-mail-Composer-input", "Dummy Message");
        await click(".o-mail-Composer-send");
    }
);

QUnit.test(
    "suggested recipients should be added as follower when posting a message",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({
            display_name: "John Jane",
            email: "john@jane.be",
        });
        const fakeId = pyEnv["res.fake"].create({ partner_ids: [partnerId] });
        const { openFormView } = await start({
            serverData: { views },
        });
        await openFormView("res.fake", fakeId);
        await click("button:contains(Send message)");
        await insertText(".o-mail-Composer-input", "Dummy Message");
        await click(".o-mail-Composer-send");
        assert.strictEqual($(".o-mail-Followers-counter").text(), "1");
    }
);

QUnit.test(
    "suggested recipient without partner are unchecked when closing the dialog without creating partner",
    async (assert) => {
        const pyEnv = await startServer();
        const fakeId = pyEnv["res.fake"].create({ email_cc: "john@test.be" });
        const { openFormView } = await start();
        await openFormView("res.fake", fakeId);
        await click("button:contains(Send message)");
        await click("label:contains(john@test.be (john@test.be))");
        await waitUntil(".modal-header");
        await click(".modal-header > button.btn-close");
        assert.containsNone($, ".form-check-input:checked");
    }
);

QUnit.test(
    "suggested recipient without partner can be clicked from the checkbox",
    async (assert) => {
        const pyEnv = await startServer();
        const fakeId = pyEnv["res.fake"].create({ email_cc: "john@test.be" });
        const { openFormView } = await start();
        await openFormView("res.fake", fakeId);
        await click("button:contains(Send message)");
        await click(".o-mail-SuggestedRecipient input");
        await waitUntil(".modal-header");
        assert.containsOnce($, ".modal-header");
    }
);
