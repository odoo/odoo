import { describe, expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { runAllTimers } from "@odoo/hoot-mock";
import {
    defineModels,
    fields,
    mockService,
    models,
    mountView,
} from "@web/../tests/web_test_helpers";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { accountModels } from "./account_test_helpers";
import { Record } from "@web/model/relational_model/record";
import { patch } from "@web/core/utils/patch";

class TestBank extends models.Model {
    _name = "test.bank";

    name = fields.Char();
    allow_out_payment = fields.Boolean();
    active = fields.Boolean({ default: true });

    _records = [
        { id: 10, name: "Bank A", allow_out_payment: true, active: true },
        { id: 20, name: "Bank B", allow_out_payment: false, active: true },
    ];
}

class TestPartner extends models.Model {
    _name = "test.partner";

    name = fields.Char();
    bank_ids = fields.Many2many({
        relation: "test.bank",
        string: "Banks",
    });

    _records = [
        {
            id: 1,
            name: "Partner 1",
            bank_ids: [10, 20],
        },
    ];

    _views = {
        form: /* xml */ `
            <form>
                <field name="bank_ids" widget="many2many_tags_banks" options="{'allow_out_payment_field': 'allow_out_payment'}"/>
            </form>
        `,
    };
}

defineModels([
    TestBank,
    TestPartner,
    ...Object.values(mailModels),
    ...Object.values(accountModels),
]);

describe("many2many_tags_banks widget", () => {
    test.tags("desktop");
    test("renders bank tags with correct trust icons based on allow_out_payment", async () => {
        await mountView({
            type: "form",
            resModel: "test.partner",
            resId: 1,
        });

        // Verify tags are rendered
        expect(".o_tag").toHaveCount(2);

        // First tag: Bank A (allow_out_payment = true)
        expect(".o_tag[data-tooltip='Bank A']").toHaveCount(1);
        expect(".o_tag[data-tooltip='Bank A'] .oi[data-icon='security'].text-success").toHaveCount(
            1
        );
        expect(
            ".o_tag[data-tooltip='Bank A'] .oi[data-icon='security'].text-success"
        ).toHaveAttribute("data-tooltip", "Trusted");

        // Second tag: Bank B (allow_out_payment = false)
        expect(".o_tag[data-tooltip='Bank B']").toHaveCount(1);
        expect(".o_tag[data-tooltip='Bank B'] .oi[data-icon='error'].text-danger").toHaveCount(1);
        expect(".o_tag[data-tooltip='Bank B'] .oi[data-icon='error'].text-danger").toHaveAttribute(
            "data-tooltip",
            "Untrusted"
        );
    });

    test.tags("desktop");
    test("archiving a tag updates the related record active state to false and removes from UI", async () => {
        let updateCalled = false;
        let updateChanges = null;
        patch(Record.prototype, {
            update(changes) {
                if (this.resModel === "test.bank") {
                    updateCalled = true;
                    updateChanges = changes;
                }
                return super.update(...arguments);
            },
        });

        await mountView({
            type: "form",
            resModel: "test.partner",
            resId: 1,
            mode: "edit",
        });

        expect(".o_tag").toHaveCount(2);

        // Click delete on Bank A (id: 10)
        await click(".o_tag[data-tooltip='Bank A'] a.o_delete");
        await runAllTimers();

        // Verify tag is removed from the UI
        expect(".o_tag").toHaveCount(1);
        expect(".o_tag[data-tooltip='Bank A']").toHaveCount(0);

        // Verify update was called on the bank record with active: false
        expect(updateCalled).toBe(true);
        expect(updateChanges).toEqual({ active: false });
    });

    test.tags("desktop");
    test("clicking the external link button triggers action service doAction to open banks list view", async () => {
        mockService("action", {
            doAction(action, options) {
                expect.step("doAction");
                expect(action).toEqual({
                    type: "ir.actions.act_window",
                    name: "Banks",
                    res_model: "test.bank",
                    views: [
                        [false, "list"],
                        [false, "form"],
                    ],
                    domain: [],
                    target: "current",
                });
                expect(options).toEqual({ newWindow: false });
            },
        });

        await mountView({
            type: "form",
            resModel: "test.partner",
            resId: 1,
            mode: "edit",
        });

        expect(".o_external_button").toHaveCount(1);
        await click(".o_external_button");

        expect.verifySteps(["doAction"]);
    });

    test.tags("desktop");
    test("saves root record if dirty when mounting", async () => {
        let saveCalled = false;
        patch(Record.prototype, {
            async isDirty() {
                return true;
            },
            async save() {
                saveCalled = true;
                return true;
            },
        });

        await mountView({
            type: "form",
            resModel: "test.partner",
            resId: 1,
        });
        await runAllTimers();

        // The record is dirty on mount, so save should be triggered.
        expect(saveCalled).toBe(true);
    });

    test.tags("desktop");
    test("does not save root record if clean when mounting", async () => {
        let saveCalled = false;
        patch(Record.prototype, {
            async isDirty() {
                return false;
            },
            async save() {
                saveCalled = true;
                return true;
            },
        });

        await mountView({
            type: "form",
            resModel: "test.partner",
            resId: 1,
        });
        await runAllTimers();

        // The record is clean on mount, so save should not be triggered.
        expect(saveCalled).toBe(false);
    });
});
