/** @odoo-module **/

import { start, startServer } from "@mail/../tests/helpers/test_utils";

import testUtils from "web.test_utils";
import { getFixture, selectDropdownItem } from "@web/../tests/helpers/utils";

let target;
QUnit.module("FieldMany2ManyTagsEmail", {
    async beforeEach() {
        target = getFixture();
    },
});

QUnit.test("fieldmany2many tags email (edition)", async function (assert) {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { name: "gold", email: "coucou@petite.perruche" },
        { name: "silver", email: "" },
    ]);
    const messageId = pyEnv["mail.message"].create({ partner_ids: [partnerId_1] });
    const views = {
        "mail.message,false,form": `
            <form string="Partners">
                <sheet>
                    <field name="body"/>
                    <field name="partner_ids" widget="many2many_tags_email"/>
                </sheet>
            </form>`,
        "res.partner,false,form":
            '<form string="Types"><field name="name"/><field name="email"/></form>',
    };
    const { openView } = await start({
        serverData: { views },
        mockRPC(route, args) {
            if (args.method === "read" && args.model === "res.partner") {
                assert.step(JSON.stringify(args.args[0]));
                assert.ok(args.args[1].includes("email"));
            } else if (args.method === "get_formview_id") {
                return false;
            }
        },
    });
    await openView(
        {
            res_id: messageId,
            res_model: "mail.message",
            views: [[false, "form"]],
        },
        { mode: "edit" }
    );

    assert.verifySteps([`[${partnerId_1}]`]);
    assert.containsOnce(
        target,
        '.o_field_many2many_tags_email[name="partner_ids"] .badge.o_tag_color_0'
    );

    // add an other existing tag
    await selectDropdownItem(target, "partner_ids", "silver");
    assert.containsOnce(
        target,
        ".modal-content .o_form_view",
        "there should be one modal opened to edit the empty email"
    );
    assert.strictEqual(
        document.querySelector(".modal-content .o_form_view .o_input#name").value,
        "silver",
        "the opened modal in edit mode should be a form view dialog with the res.partner 14"
    );
    assert.containsOnce(target, ".modal-content .o_form_view .o_input#email");

    // set the email and save the modal (will rerender the form view)
    await testUtils.fields.editInput(
        $(".modal-content .o_form_view .o_input#email"),
        "coucou@petite.perruche"
    );
    await testUtils.dom.click($(".modal-content .o_form_button_save"));
    assert.containsN(
        target,
        '.o_field_many2many_tags_email[name="partner_ids"] .badge.o_tag_color_0',
        2
    );
    const firstTag = document.querySelector(
        '.o_field_many2many_tags_email[name="partner_ids"] .badge.o_tag_color_0'
    );
    assert.strictEqual(
        firstTag.querySelector(".o_badge_text").innerText,
        "gold",
        "tag should only show name"
    );
    assert.hasAttrValue(firstTag.querySelector(".o_badge_text"), "title", "coucou@petite.perruche");
    // should have read Partner_1 three times: when opening the dropdown, when opening the modal, and
    // after the save
    assert.verifySteps([`[${partnerId_2}]`, `[${partnerId_2}]`, `[${partnerId_2}]`]);
});

QUnit.test("many2many_tags_email widget can load more than 40 records", async function (assert) {
    const pyEnv = await startServer();
    const partnerIds = [];
    for (let i = 100; i < 200; i++) {
        partnerIds.push(pyEnv["res.partner"].create({ display_name: `partner${i}` }));
    }
    const messageId = pyEnv["mail.message"].create({ partner_ids: partnerIds });
    const views = {
        "mail.message,false,form":
            '<form><field name="partner_ids" widget="many2many_tags"/></form>',
    };
    const { openView } = await start({ serverData: { views } });
    await openView({
        res_id: messageId,
        res_model: "mail.message",
        views: [[false, "form"]],
    });

    assert.containsN(target, '.o_field_widget[name="partner_ids"] .badge', 100);
    assert.containsOnce(target, ".o_form_editable");

    // add a record to the relation
    await selectDropdownItem(target, "partner_ids", "Public user");
    assert.containsN(target, '.o_field_widget[name="partner_ids"] .badge', 101);
});
