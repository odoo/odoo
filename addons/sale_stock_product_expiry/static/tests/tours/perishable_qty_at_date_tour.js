import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_forecast_widget_perishable_qty_at_date", {
    steps: () => [
        {
            trigger: "div.o_widget_qty_at_date_widget:first() > a",
            run: "click",
        },
        {
            trigger: "div.o_popover tr:has(td:nth-child(1)>strong:contains('Fresh Forecasted Stock')):has(td:nth-child(1)>small:contains('10/06/2025')):has(td:nth-child(2)>b:contains('200'))",
        },
        {
            trigger: "div.o_widget_qty_at_date_widget:last() > a",
            run: "click",
        },
        {
            trigger: "div.o_popover tr:has(td:nth-child(1)>strong:contains('Fresh Forecasted Stock')):has(td:nth-child(1)>small:contains('10/11/2025')):has(td:nth-child(2)>b:contains('100'))",
        },
    ],
});
