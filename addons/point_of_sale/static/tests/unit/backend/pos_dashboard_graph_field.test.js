import { expect, test } from "@odoo/hoot";
import { allowTranslations, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { localization } from "@web/core/l10n/localization";
import { PosDashboardGraphField } from "@point_of_sale/backend/pos_kanban_view/pos_dashboard_graph_field";

test("tooltip shows day sales and 7-day total", () => {
    allowTranslations();
    patchWithCleanup(localization, { decimalPoint: ".", thousandsSep: ",", grouping: [3, 0] });
    const field = Object.assign(Object.create(PosDashboardGraphField.prototype), {
        data: [
            {
                values: [
                    { x: "13 Oct", y: 40 },
                    { x: "14 Oct", y: 150 },
                ],
            },
        ],
        props: { record: { data: { currency_id: { id: 1 } } } },
    });
    const { title, label } = field.getLineChartConfig().options.plugins.tooltip.callbacks;
    expect(title([{ label: "14 Oct", raw: { y: 150 } }])).toBe("14 Oct: $ 150.00");
    expect(label()).toBe("Sales Last 7 Days: $ 190.00");
});
