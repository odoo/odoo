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
import { clickFieldDropdown, clickFieldDropdownItem, onRpc } from "@web/../tests/web_test_helpers";
import { queryAll } from "@odoo/hoot-dom";
import { ResPartner } from "../../mock_server/mock_models/res_partner";

defineMailModels();
describe.current.tags("desktop");

beforeEach(() => {
    ResPartner._views.form = /* xml */ `
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
        { name: "", email: "", type: "invoice" },
    ]);
    pyEnv["res.partner"].write([partnerId_2], { parent_id: partnerId_1 });
    const messageId = pyEnv["mail.message"].create({ partner_ids: [partnerId_1] });
    onRpc("res.partner", "web_read", (params) => {
        expect(params.kwargs.specification).toInclude("email");
        expect.step(`web_read ${JSON.stringify(params.args[0])}`);
    });
    onRpc("res.partner", "web_save", (params) => {
        expect(params.kwargs.specification).toInclude("email");
        expect.step(`web_save ${JSON.stringify(params.args[0])}`);
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
    await expect.waitForSteps([]);
    await contains('.o_field_many2many_tags_email[name="partner_ids"] .badge.o_tag_color_0');
    await clickFieldDropdown("partner_ids");
    await clickFieldDropdownItem("partner_ids", "gold, Invoice");
    const tags = queryAll('.o_field_many2many_tags_email[name="partner_ids"] .badge.o_tag_color_0');
    expect(tags[1].innerText).toBe("gold, Invoice");
    await contains(".o-mail-RecipientsInputTagsListPopover");
    // set the email
    await insertText(".o-mail-RecipientsInputTagsListPopover input", "coucou@petite.perruche");
    await click(".o-mail-RecipientsInputTagsListPopover .btn-primary");
    await contains('.o_field_many2many_tags_email[name="partner_ids"] .badge.o_tag_color_0', {
        count: 2,
    });
    expect(tags[0].innerText).toBe("gold");
    expect(tags[0]).toHaveAttribute("data-tooltip", "coucou@petite.perruche");
    // should have read Partner_2 2 times: when opening the dropdown and when saving the new email.
    await expect.waitForSteps([`web_read [${partnerId_2}]`, `web_save [${partnerId_2}]`]);
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
    await contains(".o-mail-RecipientsInputTagsListPopover");
    // set the email
    await insertText(".o-mail-RecipientsInputTagsListPopover input", "coucou@petite.perruche");
    // Close the modal dialog without saving (should remove partner from invalid records)
    await click(".o-mail-RecipientsInputTagsListPopover .btn-secondary");
    // Selecting a partner with a valid email shouldn't open the modal dialog for the previous partner
    await contains(".o_field_widget[name='partner_ids'] .badge", { count: 0 });
    await clickFieldDropdown("partner_ids");
    await clickFieldDropdownItem("partner_ids", "Valid Valeria");
    await contains(".o-mail-RecipientsInputTagsListPopover", { count: 0 });
});

test("many2many_tags_email expands to show all tags when focused", async () => {
    const pyEnv = await startServer();
    const partnerIds = pyEnv["res.partner"].create([
        { name: "1", email: "1" },
        { name: "2", email: "2" },
        { name: "3", email: "3" },
        { name: "4", email: "" },
    ]);
    const messageId = pyEnv["mail.message"].create({ partner_ids: partnerIds.slice(0, 3) });
    await start();
    await openFormView("mail.message", messageId, {
        arch: `
            <form>
                <field name="partner_ids" widget="many2many_tags_email" options="{'tag_limit': 2}"/>
            </form>
        `,
    });
    await contains(".o_field_widget[name='partner_ids'] .badge", { count: 2 });
    await click(".o_field_widget[name='partner_ids'] .o_field_many2many_selection input"); // Editing tags should show all
    await contains(".o_field_widget[name='partner_ids'] .badge", { count: 3 });

    // Adding tags should also keep showing all tags even if the mail popover appears
    await clickFieldDropdownItem("partner_ids", "4");
    await contains(".o-mail-RecipientsInputTagsListPopover");
    await contains(".o_field_widget[name='partner_ids'] .badge", { count: 4 }); // 1 new record, even if not valid email yet

    await insertText(".o-mail-RecipientsInputTagsListPopover input", "coucou@petite.perruche");
    await click(".o-mail-RecipientsInputTagsListPopover .btn-primary");
    await contains(".o_field_widget[name='partner_ids'] .badge", { count: 4 }); // 1 new record, email validated

    // Deleting tags should also keep showing all tags
    await click(".o_tags_input .o_tag:first-child .o_delete");
    await contains(".o_field_widget[name='partner_ids'] .badge", { count: 3 });
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
        arch: `
            <form>
            <field name='partner_ids' widget='many2many_tags' options="{'tag_limit': 0}"/>
            </form>`,
    });
    await contains('.o_field_widget[name="partner_ids"] .badge', { count: 100 });
    await contains(".o_form_editable");
    await clickFieldDropdown("partner_ids");
    await clickFieldDropdownItem("partner_ids", "Public user");
    await contains('.o_field_widget[name="partner_ids"] .badge', { count: 101 });
});
