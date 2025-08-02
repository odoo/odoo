import { expect, test } from "@odoo/hoot";
import { defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";
import { queryOne } from "@odoo/hoot-dom";

defineWebsiteModels();

test.tags("desktop");
test("should not allow edition of currency sign of monetary fields", async () => {
    await setupWebsiteBuilder(
        `<span data-oe-model="product.template" data-oe-id="9" data-oe-field="list_price" data-oe-type="monetary" data-oe-expression="product.list_price">
            $&nbsp;<span class="oe_currency_value">750.00</span>
        </span>`
    );
    expect(queryOne(":iframe span[data-oe-type]").isContentEditable).toBe(false);
    expect(queryOne(":iframe span.oe_currency_value").isContentEditable).toBe(true);
});
