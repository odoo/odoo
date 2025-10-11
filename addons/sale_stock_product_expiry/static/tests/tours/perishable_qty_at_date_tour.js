import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('test_perishable_qty_at_date', {
    steps: () => [
        {
            trigger: "div.o_widget_qty_at_date_widget > a",
            run: "click",
        },
        {
            trigger: "div.o_popover tr:contains('Fresh Forecasted Stock')",
            run: () => {
                const widgetRows = document.querySelectorAll("div.o_popover tr");
                const FreshStockRow = Array.from(widgetRows).find(row => row.innerText.includes("Fresh Forecasted Stock"));
                let valid = false;
                if (!FreshStockRow) {
                    throw new Error("No row found for Fresh Forecasted Stock");
                }
                if (FreshStockRow.innerText.includes("10/06/2025")) {
                    valid = FreshStockRow.querySelector("b").innerText === "200";
                }
                else if (FreshStockRow.innerText.includes("10/11/2025")) {
                    valid = FreshStockRow.querySelector("b").innerText === "100";
                }
                if (!valid) {
                    throw new Error("Fresh Forecasted Stock should be 200 on 10/06/2025 and 100 on 10/11/2025");
                }
            }
        },
    ],
});
