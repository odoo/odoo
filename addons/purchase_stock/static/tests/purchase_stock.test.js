import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { describe, destroy, expect, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { contains, defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

class PurchaseOrderSuggest extends models.Model {
    _name = "purchase.order.suggest";
    based_on = fields.Selection({
        selection: [
            ["actual_demand", "Forecasted"],
            ["one_week", "Last 7 days"],
            ["30_days", "Last 30 days"],
            ["three_months", "Last 3 months"],
            ["one_year", "Last 12 months"],
            ["last_year", "Same month last year"],
            ["last_year_m_plus_1", "Next month last year"],
            ["last_year_m_plus_2", "After next month last year"],
            ["last_year_quarter", "Last year quarter"],
        ],
        default: "30_days",
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
        await contains(".o_field_widget[name='based_on'] input").click();
        expect(".o_select_menu_menu .o_select_menu_item:nth-last-child(4)").toHaveText("November 2024");
        expect(".o_select_menu_menu .o_select_menu_item:nth-last-child(3)").toHaveText("December 2024");
        expect(".o_select_menu_menu .o_select_menu_item:nth-last-child(2)").toHaveText("January 2025");
        expect(".o_select_menu_menu .o_select_menu_item:last-child").toHaveText("Nov 2024-Jan 2025");
        destroy(view);
        // Check for a different date.
        mockDate("2020-03-20 07:00:00");
        await mountView({
            type: "form",
            resModel: "purchase.order.suggest",
        });
        await contains(".o_field_widget[name='based_on'] input").click();
        expect(".o_select_menu_menu .o_select_menu_item:nth-last-child(4)").toHaveText("March 2019");
        expect(".o_select_menu_menu .o_select_menu_item:nth-last-child(3)").toHaveText("April 2019");
        expect(".o_select_menu_menu .o_select_menu_item:nth-last-child(2)").toHaveText("May 2019");
        expect(".o_select_menu_menu .o_select_menu_item:last-child").toHaveText("Mar-May 2019");
    });
});
