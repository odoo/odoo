import { describe, expect, test } from "@odoo/hoot";
import { setInputFiles } from "@odoo/hoot-dom";
import {
    contains,
    defineModels,
    fields,
    mockService,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";

class Partner extends models.Model {
    name = fields.Char();
    type = fields.Char();

    _records = [
        {
            id: 7,
            name: "first record",
            type: "purchase",
        },
    ];
    _views = {
        form: `
            <form>
                <widget name="account_file_uploader"/>
                <field name="name" required="1"/>
            </form>
        `,
        list: `
            <list>
                <field name="id"/>
                <field name="name"/>
            </list>
        `,
        search: `<search/>`,
    };
}

class AccountPaymentTerm extends models.Model {
    _name = "account_payment_term";

    line_ids = fields.One2many({
        string: "Payment Term Lines",
        relation: "account_payment_term_line",
    });
    _records = [
        {
            id: 1,
            line_ids: [1, 2],
        },
    ];
}

class AccountPaymentTermLine extends models.Model {
    _name = "account_payment_term_line";

    value_amount = fields.Float({ string: "Due" });
    _records = [
        {
            id: 1,
            value_amount: 0,
        },
        {
            id: 2,
            value_amount: 50,
        },
    ];
}

defineModels([AccountPaymentTerm, AccountPaymentTermLine, Partner]);
defineMailModels();

describe("AccountFileUploader", () => {
    test("widget contains context based on the record despite field not in view", async () => {
        onRpc("ir.attachment", "create", () => {
            expect.step("create ir.attachment");
            return [99];
        });

        onRpc("account.journal", "create_document_from_attachment", ({ kwargs }) => {
            expect.step("create_document_from_attachment");
            expect(kwargs.context.default_journal_id).toBe(7, {
                message: "create documents in correct journal",
            });
            expect(kwargs.context.default_move_type).toBe("in_invoice", {
                message: "create documents with correct move type",
            });
            return {
                name: "Generated Documents",
                domain: [],
                res_model: "partner",
                type: "ir.actions.act_window",
                context: {},
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
                view_mode: "list, form",
            };
        });
        mockService("action", {
            doAction(action) {
                expect.step("doAction");
                expect(action.type).toBe("ir.actions.act_window", {
                    message: "do action after documents created",
                });
            },
        });
        await mountView({
            type: "form",
            resModel: "partner",
            resId: 7,
        });

        expect(".o_widget_account_file_uploader").toHaveCount(1);
        const file = new File(["test"], "fake_file.txt", { type: "text/plain" });
        await contains(".o_widget_account_file_uploader a").click();
        await setInputFiles([file]);
        await expect.waitForSteps([
            "create ir.attachment",
            "create_document_from_attachment",
            "doAction",
        ]);
    });
});

describe("AccountMoveUploadKanbanView", () => {
    test.tags("desktop");
    test("can render AccountMoveUploadKanbanView", async () => {
        Partner._views.kanban = `
            <kanban js_class="account_documents_kanban">
                <templates>
                    <t t-name="card">
                        <field name="name"/>
                    </t>
                </templates>
            </kanban>
        `;
        onRpc("res.company", "search_read", () => [{ id: 1, country_code: "US" }]);
        await mountView({
            type: "kanban",
            resModel: "partner",
        });

        expect(".o_control_panel .o_button_upload_bill:visible").toHaveCount(1);
        expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(1);
    });
});

describe("PaymentTermsLineWidget", () => {
    test("records don't get abandoned after clicking globally or on an exisiting record", async () => {
        await mountView({
            type: "form",
            resModel: "account_payment_term",
            resId: 1,
            arch: `
            <form>
                <field name="line_ids" widget="payment_term_line_ids">
                    <list string="Payment Terms" editable="top">
                        <field name="value_amount"/>

                    </list>
                </field>
            </form>
            `,
        });
        expect(".o_data_row").toHaveCount(2);
        // click the add button
        await contains(".o_field_x2many_list_row_add > button").click();
        // make sure the new record is added
        expect(".o_data_row").toHaveCount(3);
        // global click
        await contains(".o_form_view").click();
        // make sure the new record is still there
        expect(".o_data_row").toHaveCount(3);
        // click the add button again
        await contains(".o_field_x2many_list_row_add > button").click();
        // make sure the new record is added
        expect(".o_data_row").toHaveCount(4);
        // click on an existing record
        await contains(".o_data_row .o_data_cell").click();
        // make sure the new record is still there
        expect(".o_data_row").toHaveCount(4);
    });
});
