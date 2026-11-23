import { describe, expect, test } from "@odoo/hoot";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";

setupInteractionWhiteList("website_sale.daterange_picker");
describe.current.tags("interaction_dev");

const deliveryMethod = (dateAttribute) => `
    <div name="o_delivery_method">
        <input type="radio" name="o_delivery_radio"/>
        <div class="o_website_sale_delivery_date_picker"
             data-delivery-estimate-dates='["2026-11-24", "2026-11-25", "2026-11-26"]'
             ${dateAttribute}>
            <input type="text" name="estimated_delivery"/>
        </div>
    </div>
`;

test("delivery date picker shows the date of the order", async () => {
    await startInteractions(deliveryMethod('data-delivery-date="2026-11-25"'));
    expect("[name=estimated_delivery]").toHaveValue("Nov 25, 2026");
});

test("delivery date picker shows the first date by default", async () => {
    await startInteractions(deliveryMethod(""));
    expect("[name=estimated_delivery]").toHaveValue("Nov 24, 2026");
});
