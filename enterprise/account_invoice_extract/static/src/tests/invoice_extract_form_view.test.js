import {
    click,
    contains,
    focus,
    openFormView,
    patchUiSize,
    SIZES,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { beforeEach, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { onRpc } from "@web/../tests/web_test_helpers";
import {
    createBoxesData,
    defineAccountInvoiceExtractModels,
} from "./account_invoice_extract_test_helpers";

defineAccountInvoiceExtractModels();

beforeEach(() => {
    patchUiSize({ size: SIZES.XXL });
});

test("basic", async () => {
    const pyEnv = await startServer();
    pyEnv["res.partner"]._views.form = /* xml */ `
        <form>
            <group>
                <field name="name" readonly="0"/>
                <field name="vat" readonly="0"/>
            </group>
        </form>
    `;
    const resCurrencyId1 = pyEnv["res.currency"].create({ name: "USD" });
    const resCurrencyId2 = pyEnv["res.currency"].create({ name: "EUR" });
    const resPartnerId1 = pyEnv["res.partner"].create({
        name: "Odoo",
        vat: "BE0477472701",
    });
    const accountMoveId1 = pyEnv["account.move"].create({
        amount_total: 100,
        currency_id: resCurrencyId1,
        date: "1984-12-15",
        invoice_date_due: "1984-12-20",
        display_name: "MyInvoice",
        invoice_date: "1984-12-15",
        state: "draft",
        move_type: "in_invoice",
        extract_state: "waiting_validation",
    });
    const irAttachmentId1 = pyEnv["ir.attachment"].create({
        mimetype: "image/jpeg",
        res_model: "account.move",
        res_id: accountMoveId1,
    });
    pyEnv["account.move"].write([accountMoveId1], {
        extract_attachment_id: irAttachmentId1,
    });
    pyEnv["mail.message"].create({
        attachment_ids: [irAttachmentId1],
        model: "account.move",
        res_id: accountMoveId1,
    });
    onRpc("account.move", "get_boxes", () => {
        return createBoxesData();
    });
    onRpc("account.move", "get_partner_create_data", () => {
        return {};
    });
    onRpc("account.move", "set_user_selected_box", (args) => {
        const boxId = args.args[1];
        switch (boxId) {
            case 1:
                return resPartnerId1;
            case 2:
                return false;
            case 4:
                return "some invoice_id";
            case 7:
                return false;
            case 8:
                return resPartnerId1;
            case 10:
                return 123;
            case 12:
                return "2022-01-01 00:00:00";
            case 14:
                return "2022-01-15 00:00:00";
            case 16:
                return resCurrencyId2;
        }
    });
    await start();
    await openFormView("account.move", accountMoveId1, {
        arch: `
        <form string="Account Invoice" js_class="account_move_form">
            <group>
                <field name="extract_state" invisible="1"/>
                <field name="state" invisible="1"/>
                <field name="move_type" invisible="1"/>
                <field name="extract_attachment_id" invisible="1"/>
                <field name="partner_id" readonly="0"/>
                <field name="ref" readonly="0"/>
                <field name="invoice_date" readonly="0"/>
                <field name="invoice_date_due" readonly="0"/>
                <field name="currency_id" readonly="0"/>
                <field name="quick_edit_total_amount" readonly="0"/>
            </group>
            <div class="o_attachment_preview"/>
            <chatter/>
        </form>`,
    });
    await contains(".o-mail-Attachment-imgContainer");
    const attachmentPreview = document.querySelector(".o-mail-Attachment-imgContainer");
    // ---------- Supplier & VAT Number ----------
    // Focus the field
    await focus(".o_field_widget[name=partner_id] input");
    // Check boxes presence for supplier & VAT number
    await contains(".o_invoice_extract_box", { count: 6 });
    await contains(".o_invoice_extract_box[data-field-name=supplier]", { count: 3 });
    await contains(".o_invoice_extract_box[data-field-name=VAT_Number]", { count: 3 });
    // Check selection of VAT number boxes
    expect(attachmentPreview.querySelector('.o_invoice_extract_box[data-id="1"]')).not.toHaveClass(
        "ocr_chosen"
    );
    expect(attachmentPreview.querySelector('.o_invoice_extract_box[data-id="1"]')).not.toHaveClass(
        "selected"
    );
    expect(attachmentPreview.querySelector('.o_invoice_extract_box[data-id="2"]')).toHaveClass(
        "ocr_chosen"
    );
    expect(attachmentPreview.querySelector('.o_invoice_extract_box[data-id="2"]')).not.toHaveClass(
        "selected"
    );
    expect(attachmentPreview.querySelector('.o_invoice_extract_box[data-id="3"]')).not.toHaveClass(
        "ocr_chosen"
    );
    expect(attachmentPreview.querySelector('.o_invoice_extract_box[data-id="3"]')).toHaveClass(
        "selected"
    );
    // Check selection of supplier boxes
    expect(attachmentPreview.querySelector('.o_invoice_extract_box[data-id="6"]')).not.toHaveClass(
        "ocr_chosen"
    );
    expect(attachmentPreview.querySelector('.o_invoice_extract_box[data-id="6"]')).toHaveClass(
        "selected"
    );
    expect(attachmentPreview.querySelector('.o_invoice_extract_box[data-id="7"]')).toHaveClass(
        "ocr_chosen"
    );
    expect(attachmentPreview.querySelector('.o_invoice_extract_box[data-id="7"]')).not.toHaveClass(
        "selected"
    );
    expect(attachmentPreview.querySelector('.o_invoice_extract_box[data-id="8"]')).not.toHaveClass(
        "ocr_chosen"
    );
    expect(attachmentPreview.querySelector('.o_invoice_extract_box[data-id="8"]')).not.toHaveClass(
        "selected"
    );
    // Click on the VAT number box with ID 1
    await click('.o_invoice_extract_box[data-id="1"]');
    await contains(".o_field_widget[name=partner_id] input", { value: "Odoo" });
    await contains('.selected.o_invoice_extract_box[data-id="1"]');
    expect(attachmentPreview.querySelector('.o_invoice_extract_box[data-id="2"]')).not.toHaveClass(
        "selected"
    );
    // Click on the VAT number box with ID 2
    await click('.o_invoice_extract_box[data-id="2"]');
    // Check that a modal opened to create a res.partner with the VAT number pre-filled
    await contains(".o_dialog input#vat_0", { value: "BE0477472701" });
    await click(".o_dialog .o_form_button_cancel");

    // Re-focus the field
    await focus(".o_field_widget[name=partner_id] input");
    // Click on the supplier box with ID 7
    await click('.o_invoice_extract_box[data-id="7"]');
    // Check that a modal opened to create a res.partner with the name pre-filled
    await contains(".o_dialog input#name_0", { value: "Some partner" });
    await click(".o_dialog .o_form_button_cancel");
    // Re-focus the field
    await focus(".o_field_widget[name=partner_id] input");
    // Click on the VAT number box with ID 8
    await click('.o_invoice_extract_box[data-id="8"]');
    await contains(".o_field_widget[name=partner_id] input", { value: "Odoo" });
    // ---------- Invoice ID ----------
    // Focus the field
    await focus(".o_field_widget[name=ref] input");
    // Check boxes presence for invoice ID
    await contains(".o_invoice_extract_box", { count: 2 });
    await contains(".o_invoice_extract_box[data-field-name=invoice_id]", { count: 2 });
    // Click on the invoice ID box with ID 4
    await click('.o_invoice_extract_box[data-id="4"]');
    await animationFrame(); // so that input value is changed (prevent relying on contains timeout)
    await contains(".o_field_widget[name=ref] input", { value: "some invoice_id" });
    // ---------- Total ----------
    // Focus the field
    await focus(".o_field_widget[name=quick_edit_total_amount] input");
    // Check boxes presence for total
    await contains(".o_invoice_extract_box", { count: 2 });
    await contains(".o_invoice_extract_box[data-field-name=total]", { count: 2 });
    // Click on the total box with ID 10
    await click('.o_invoice_extract_box[data-id="10"]');
    await contains(".o_field_widget[name=quick_edit_total_amount] input", { value: "123.00" });
    // ---------- Date ----------
    // Focus the field
    await focus(".o_field_widget[name=invoice_date] input");
    // Check boxes presence for date
    await contains(".o_invoice_extract_box", { count: 3 });
    await contains(".o_invoice_extract_box[data-field-name=date]", { count: 3 });
    // Click on the date box with ID 12
    await click('.o_invoice_extract_box[data-id="12"]');
    await contains(".o_field_widget[name=invoice_date] input", { value: "01/01/2022" });
    // ---------- Due date ----------
    // Focus the field
    await focus(".o_field_widget[name=invoice_date_due] input");
    // Check boxes presence for due date
    await contains(".o_invoice_extract_box", { count: 2 });
    await contains(".o_invoice_extract_box[data-field-name=due_date]", { count: 2 });
    // Click on the due date box with ID 14
    await click('.o_invoice_extract_box[data-id="14"]');
    await contains(".o_field_widget[name=invoice_date_due] input", { value: "01/15/2022" });
    // ---------- Currency ----------
    // Focus the field
    await focus(".o_field_widget[name=currency_id] input");
    // Check boxes presence for currency
    await contains(".o_invoice_extract_box", { count: 2 });
    await contains(".o_invoice_extract_box[data-field-name=currency]", { count: 2 });
    // Click on the currency box with ID 16
    await click('.o_invoice_extract_box[data-id="16"]');
    await contains(".o_field_widget[name=currency_id] input", { value: "EUR" });
});
