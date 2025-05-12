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
    await contains(".o-mail-RecipientsInputTagsListPopover");
    // set the email
    await insertText(".o-mail-RecipientsInputTagsListPopover input", "coucou@petite.perruche");
    await click(".o-mail-RecipientsInputTagsListPopover .btn-primary");
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
    // should have read Partner_2 2 times: when opening the dropdown and when saving the new email.
    await waitForSteps([`[${partnerId_2}]`,`[${partnerId_1},${partnerId_2}]`]);
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

test("many2many_tags_email widget shows email if name is null", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "",
        email: "normal_valid_email@test.com",
    });

    // Simulate the action that opens the mail.compose.message wizard
    const wizardId = pyEnv["mail.compose.message"].create({
        partner_ids: [partnerId],
        subject: "Test Subject",
        body: "<p>Hello</p>",
    });

    await start();

    await openFormView("mail.compose.message", wizardId, {
        arch: `
            <form string="Send">
                <field name="partner_ids" widget="many2many_tags_email"/>
                <field name="subject"/>
                <field name="body"/>
                <footer>
                    <button string="Send" type="object" name="send_mail"/>
                </footer>
            </form>
        `,
    });

    await contains('.o_field_widget[name="partner_ids"] .badge', { count: 1 });

    // Now check the text content of the badge to verify it shows the email
    const badge = document.querySelector('.o_field_many2many_tags_email[name="partner_ids"] .badge');
    expect(badge?.textContent).toBe("normal_valid_email@test.com");
});
