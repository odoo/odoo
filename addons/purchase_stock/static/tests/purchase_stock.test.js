import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { describe, destroy, expect, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import {
    defineModels,
    fields,
    models,
    mountView,
} from "@web/../tests/web_test_helpers";

class PurchaseOrderSuggest extends models.Model {
    _name = "purchase.order.suggest";
    based_on = fields.Selection({
        selection: [
            ["one_week", "Last 7 days"],
            ["one_month", "Last 30 days"],
            ["three_months", "Last 3 months"],
            ["one_year", "Last 12 months"],
            ["last_year", "Same month last year"],
            ["last_year_2", "Next month last year"],
            ["last_year_3", "After next month last year"],
            ["last_year_quarter", "Last year quarter"],
        ],
        default: "one_month",
        string: "Based on",
    });
    _views = {
        form: `
            <form>
                <sheet>
                    <field name="based_on" widget="time_period_selection"/>
                </sheet>
            </form>
        `,
    };
}
defineModels([PurchaseOrderSuggest]);
defineMailModels();

describe("time_period_selection field", () => {
    test("relative selection options", async () => {
        mockDate("2025-11-15 07:00:00");
        const view = await mountView({
            type: "form",
            resModel: "purchase.order.suggest",
        });
        expect("select option:nth-last-child(4)").toHaveText("November 2024");
        expect("select option:nth-last-child(3)").toHaveText("December 2024");
        expect("select option:nth-last-child(2)").toHaveText("January 2025");
        expect("select option:last-child").toHaveText("Nov 2024-Jan 2025");
        destroy(view);
        // Check for a different date.
        mockDate("2020-03-20 07:00:00");
        await mountView({
            type: "form",
            resModel: "purchase.order.suggest",
        });
        expect("select option:nth-last-child(4)").toHaveText("March 2019");
        expect("select option:nth-last-child(3)").toHaveText("April 2019");
        expect("select option:nth-last-child(2)").toHaveText("May 2019");
        expect("select option:last-child").toHaveText("Mar-May 2019");
    });
});
