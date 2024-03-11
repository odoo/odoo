/** @odoo-module alias=@mail/../tests/web/fields/many2many_tags_email_tests default=false */
const test = QUnit.test; // QUnit.test()

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { openFormView, start } from "@mail/../tests/helpers/test_utils";

import { selectDropdownItem } from "@web/../tests/helpers/utils";
import { assertSteps, click, contains, insertText, step } from "@web/../tests/utils";

QUnit.module("FieldMany2ManyTagsEmail");

test("fieldmany2many tags email (edition)", async (assert) => {
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
        "res.partner,false,form": `
            <form string="Types">
                <field name="name"/>
                <field name="email"/>
            </form>`,
    };
    await start({
        serverData: { views },
        mockRPC(route, args) {
            if (args.method === "web_read" && args.model === "res.partner") {
                step(JSON.stringify(args.args[0]));
                assert.ok("email" in args.kwargs.specification);
            } else if (args.method === "get_formview_id") {
                return false;
            }
        },
    });
    await openFormView("mail.message", messageId, { props: { mode: "edit" } });
    await assertSteps([]);
    await contains('.o_field_many2many_tags_email[name="partner_ids"] .badge.o_tag_color_0');

    // add an other existing tag
    await selectDropdownItem(document.body, "partner_ids", "silver");
    await contains(".modal-content .o_form_view");
    await contains(".modal-content .o_form_view .o_input#name_0", { value: "silver" });
    await contains(".modal-content .o_form_view .o_input#email_0");

    // set the email and save the modal (will rerender the form view)
    await insertText(".modal-content .o_form_view .o_input#email_0", "coucou@petite.perruche");
    await click(".modal-content .o_form_button_save");
    await contains('.o_field_many2many_tags_email[name="partner_ids"] .badge.o_tag_color_0', {
        count: 2,
    });
    const firstTag = $('.o_field_many2many_tags_email[name="partner_ids"] .badge.o_tag_color_0')[0];
    assert.strictEqual(
        firstTag.querySelector(".o_badge_text").innerText,
        "gold",
        "tag should only show name"
    );
    assert.hasAttrValue(firstTag.querySelector(".o_badge_text"), "title", "coucou@petite.perruche");
    // should have read Partner_1 three times: when opening the dropdown, when opening the modal, and
    // after the save
    await assertSteps([`[${partnerId_2}]`, `[${partnerId_2}]`, `[${partnerId_1},${partnerId_2}]`]);
});

test("many2many_tags_email widget can load more than 40 records", async () => {
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
    await start({ serverData: { views } });
    await openFormView("mail.message", messageId);
    await contains('.o_field_widget[name="partner_ids"] .badge', { count: 100 });
    await contains(".o_form_editable");

    // add a record to the relation
    await selectDropdownItem(document.body, "partner_ids", "Public user");
    await contains('.o_field_widget[name="partner_ids"] .badge', { count: 101 });
});
