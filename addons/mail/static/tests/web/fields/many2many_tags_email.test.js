import { beforeEach, describe, expect, test } from "@odoo/hoot";
import {
    click,
    contains,
    defineMailModels,
    insertText,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import {
    asyncStep,
    clickFieldDropdown,
    clickFieldDropdownItem,
    onRpc,
    waitForSteps,
} from "@web/../tests/web_test_helpers";
import { queryFirst } from "@odoo/hoot-dom";
import { ResPartner } from "../../mock_server/mock_models/res_partner";

defineMailModels();
describe.current.tags("desktop");

beforeEach(() => {
    ResPartner._views["form,false"] = `
        <form>
            <field name="name"/>
            <field name="email"/>
        </form>
    `;
});

test("fieldmany2many tags email (edition)", async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { name: "gold", email: "coucou@petite.perruche" },
        { name: "silver", email: "" },
    ]);
    const messageId = pyEnv["mail.message"].create({ partner_ids: [partnerId_1] });
    onRpc("res.partner", "web_read", (params) => {
        expect(params.kwargs.specification).toInclude("email");
        asyncStep(JSON.stringify(params.args[0]));
    });
    onRpc("res.partner", "get_formview_id", () => false);
    await start();
    await openFormView("mail.message", messageId, {
        arch: `
            <form>
                <field name="body"/>
                <field name="partner_ids" widget="many2many_tags_email"/>
            </form>
        `,
    });
    await waitForSteps([]);
    await contains('.o_field_many2many_tags_email[name="partner_ids"] .badge.o_tag_color_0');
    await clickFieldDropdown("partner_ids");
    await clickFieldDropdownItem("partner_ids", "silver");
    await contains(".modal-content .o_form_view .o_input#name_0", { value: "silver" });
    await contains(".modal-content .o_form_view .o_input#email_0");
    // set the email and save the modal (will rerender the form view)
    await insertText(".modal-content .o_form_view .o_input#email_0", "coucou@petite.perruche");
    await click(".modal-content .o_form_button_save");
    await contains('.o_field_many2many_tags_email[name="partner_ids"] .badge.o_tag_color_0', {
        count: 2,
    });
    const firstTag = queryFirst(
        '.o_field_many2many_tags_email[name="partner_ids"] .badge.o_tag_color_0'
    );
    expect(firstTag.innerText).toBe("gold");
    expect(firstTag.querySelector(".o_badge_text")).toHaveAttribute(
        "title",
        "coucou@petite.perruche"
    );
    // should have read Partner_1 three times: when opening the dropdown, when opening the modal, and
    // after the save
    await waitForSteps([`[${partnerId_2}]`, `[${partnerId_2}]`, `[${partnerId_1},${partnerId_2}]`]);
});

test("fieldmany2many tags email popup close without filling", async () => {
    const pyEnv = await startServer();
    pyEnv["res.partner"].create([
        { name: "Valid Valeria", email: "normal_valid_email@test.com" },
        { name: "Deficient Denise", email: "" },
    ]);
    onRpc("res.partner", "get_formview_id", () => false);
    await start();
    await openFormView("mail.message", undefined, {
        arch: `
            <form>
                <field name="body"/>
                <field name="partner_ids" widget="many2many_tags_email"/>
            </form>
        `,
    });
    // add an other existing tag
    await clickFieldDropdown("partner_ids");
    await clickFieldDropdownItem("partner_ids", "Deficient Denise");
    await contains(".modal-content .o_form_view");
    await contains(".modal-content .o_form_view .o_input#name_0", { value: "Deficient Denise" });
    await contains(".modal-content .o_form_view .o_input#email_0", { value: "" });
    // Close the modal dialog without saving (should remove partner from invalid records)
    await click(".modal-content .o_form_button_cancel");
    // Selecting a partner with a valid email shouldn't open the modal dialog for the previous partner
    await clickFieldDropdown("partner_ids");
    await clickFieldDropdownItem("partner_ids", "Valid Valeria");
    await contains(".modal-content .o_forw_view", { count: 0 });
});

test("many2many_tags_email widget can load more than 40 records", async () => {
    const pyEnv = await startServer();
    const partnerIds = [];
    for (let i = 100; i < 200; i++) {
        partnerIds.push(pyEnv["res.partner"].create({ display_name: `partner${i}` }));
    }
    const messageId = pyEnv["mail.message"].create({ partner_ids: partnerIds });
    await start();
    await openFormView("mail.message", messageId, {
        arch: "<form><field name='partner_ids' widget='many2many_tags'/></form>",
    });
    await contains('.o_field_widget[name="partner_ids"] .badge', { count: 100 });
    await contains(".o_form_editable");
    await clickFieldDropdown("partner_ids");
    await clickFieldDropdownItem("partner_ids", "Public user");
    await contains('.o_field_widget[name="partner_ids"] .badge', { count: 101 });
});
