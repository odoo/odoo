import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import {
    defineModels,
    defineWebModels,
    fields,
    models,
    mountView,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { GloryService } from "@pos_glory_cash/glory_service";
import { GloryAdminButtons } from "@pos_glory_cash/backend/glory_admin_buttons/glory_admin_buttons";

class PaymentMethod extends models.Model {
    glory_websocket_address = fields.Char();
    glory_username = fields.Char();
    glory_password = fields.Char();
    name = fields.Char();
    _records = [
        {
            id: 1,
            glory_websocket_address: "machine",
            glory_username: "cashier",
            glory_password: "secret",
            name: "Cash",
        },
    ];
}
defineWebModels();
defineModels([PaymentMethod]);

test("connection follows credential changes while record data keeps its identity", async () => {
    let record;
    patchWithCleanup(GloryAdminButtons.prototype, {
        setup() {
            super.setup();
            record = this.props.record;
        },
    });
    patchWithCleanup(GloryService.prototype, {
        connect(...args) {
            expect.step(args);
        },
    });
    await mountView({
        resModel: "payment.method",
        type: "form",
        resId: 1,
        arch: `<form>
            <field name="name"/>
            <field name="glory_websocket_address"/>
            <field name="glory_username"/>
            <field name="glory_password"/>
            <widget name="pos_glory_cash_admin_buttons"/>
        </form>`,
    });
    expect.verifySteps([["machine", "cashier", "secret"]]);
    const data = record.data;
    for (const [field, value, credentials] of [
        [
            "glory_websocket_address",
            "new-machine",
            ["new-machine", "cashier", "secret"],
        ],
        ["glory_username", "manager", ["new-machine", "manager", "secret"]],
        ["glory_password", "new-secret", ["new-machine", "manager", "new-secret"]],
    ]) {
        await record.update({ [field]: value });
        await animationFrame();
        expect(record.data).toBe(data);
        expect.verifySteps([credentials]);
    }
    await record.update({ name: "Renamed" });
    await animationFrame();
    expect.verifySteps([]);
});
