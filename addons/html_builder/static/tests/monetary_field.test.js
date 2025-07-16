import { expect, test } from "@odoo/hoot";
import { setupHTMLBuilder } from "./helpers";

test("should not allow edition of currency sign of monetary fields", async () => {
    await setupHTMLBuilder(
        `<span data-oe-model="product.template" data-oe-id="9" data-oe-field="list_price" data-oe-type="monetary" data-oe-expression="product.list_price">
            $&nbsp;<span class="oe_currency_value">750.00</span>
        </span>`
    );
    expect(":iframe span[data-oe-type]").toHaveProperty("isContentEditable", false);
    expect(":iframe span.oe_currency_value").toHaveProperty("isContentEditable", true);
});
