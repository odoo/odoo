import { expect, test } from "@odoo/hoot";
import { defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";
import { defineAccountModels } from "@account/../tests/account_test_helpers";

class AccountPayment extends models.Model {
    _name = "account.payment";

    withhold = fields.Selection({
        selection: [
            ["withhold_pay", "Withhold and Pay"],
            ["withhold", "Withhold Only"],
            ["payment", "Payment Only"],
        ],
    });
    available_withhold_values = fields.Json();
    reconciled_bills_count = fields.Integer();

    _records = [
        { id: 1, withhold: "withhold_pay", available_withhold_values: ["withhold", "payment"], reconciled_bills_count: 1 },
        { id: 2, withhold: "payment", available_withhold_values: ["withhold", "payment"], reconciled_bills_count: 1 },
        { id: 3, withhold: "payment", reconciled_bills_count: 0 },
    ];
}

defineAccountModels();
defineModels([AccountPayment]);

const whitelistArch = /* xml */ `
    <form>
        <field name="available_withhold_values" invisible="1"/>
        <field name="reconciled_bills_count" invisible="1"/>
        <field name="withhold" widget="withhold_selector" options="{'whitelist_fname': 'available_withhold_values'}"/>
    </form>
`;

test("withhold_selector only offers whitelisted values", async () => {
    await mountView({ type: "form", resModel: "account.payment", resId: 2, arch: whitelistArch });
    expect(".o_field_withhold_selector").toHaveText("Withhold Only\nPayment Only");
});

test("withhold_selector keeps the current value even if not whitelisted", async () => {
    await mountView({ type: "form", resModel: "account.payment", resId: 1, arch: whitelistArch });
    expect(".o_field_withhold_selector").toHaveText("Withhold and Pay\nWithhold Only\nPayment Only");
    expect("input[data-value=withhold_pay]").toBeChecked();
});

test("withhold_selector hides Withhold Only without a reconciled bill", async () => {
    await mountView({
        type: "form",
        resModel: "account.payment",
        resId: 3,
        arch: /* xml */ `
            <form>
                <field name="reconciled_bills_count" invisible="1"/>
                <field name="withhold" widget="withhold_selector"/>
            </form>
        `,
    });
    expect(".o_field_withhold_selector").toHaveText("Withhold and Pay\nPayment Only");
});
