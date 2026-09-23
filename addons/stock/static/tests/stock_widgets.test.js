import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import { useOperationGuard } from "@stock/utils/use_operation_guard";
import {
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

class StockThing extends models.Model {
    _name = "stock.thing";
    forecast_availability = fields.Float();
    product_qty = fields.Float();
    date_planned_forecast = fields.Datetime();
    date_deadline = fields.Datetime();
    is_storable = fields.Boolean();
    state = fields.Char();
    package_id = fields.Many2one({ relation: "stock.package" });
    _records = [
        {
            id: 1,
            forecast_availability: 10,
            product_qty: 4,
            is_storable: true,
            state: "assigned",
        },
        {
            id: 2,
            forecast_availability: 1,
            product_qty: 4,
            is_storable: true,
            state: "done",
        },
    ];
}
class StockPackage extends models.Model {
    _name = "stock.package";
    name = fields.Char();
    _records = [{ id: 1, name: "PARENT > CHILD" }];
}
defineModels([StockThing, StockPackage]);
defineMailModels();

describe("forecast_widget", () => {
    async function mountForecast(resId) {
        onRpc("has_group", () => false);
        await mountView({
            type: "form",
            resModel: "stock.thing",
            resId,
            arch: `<form><field name="forecast_availability" widget="forecast_widget"/></form>`,
        });
    }

    test("a covered forecast reads as available", async () => {
        await mountForecast(1);
        expect(".badge").toHaveCount(1);
        expect(".badge").toHaveText("Available");
        expect(".badge").toHaveClass("text-bg-success");
    });

    test("a shortfall reads as not available", async () => {
        await mountForecast(2);
        expect(".badge").toHaveText("Not Available");
        expect(".badge").toHaveClass("text-bg-danger");
    });

    test("it is a real button, so it is reachable from the keyboard", async () => {
        await mountForecast(1);
        expect("button.badge").toHaveCount(1);
    });
});

describe("useOperationGuard", () => {
    class Guarded extends Component {
        static template = xml`
            <button class="go" t-att-disabled="this.guard.busy" t-on-click="this.run">go</button>`;
        static props = ["onRun"];
        setup() {
            this.guard = useOperationGuard();
            this.run = this.guard.guard(() => this.props.onRun());
        }
    }

    test("a second call is dropped while the first is in flight", async () => {
        const inFlight = new Deferred();
        let calls = 0;
        await mountWithCleanup(Guarded, {
            props: {
                onRun: () => {
                    calls++;
                    return inFlight;
                },
            },
        });
        await click(".go");
        await animationFrame();
        expect(".go").toHaveAttribute("disabled");
        await click(".go");
        await animationFrame();
        expect(calls).toBe(1);
        inFlight.resolve();
        await animationFrame();
        expect(calls).toBe(1);
    });

    test("the flag is released even when the operation rejects", async () => {
        let calls = 0;
        const component = await mountWithCleanup(Guarded, {
            props: {
                onRun: () => {
                    calls++;
                    return Promise.reject(new Error("boom"));
                },
            },
        });
        await component.run().catch(() => {});
        await animationFrame();
        expect(component.guard.busy).toBe(false);
        await component.run().catch(() => {});
        expect(calls).toBe(2);
    });
});
