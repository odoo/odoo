import { setupHTMLBuilder } from "@html_builder/../tests/helpers";
import { expect, test, describe } from "@odoo/hoot";
import { click, queryOne } from "@odoo/hoot-dom";

describe.current.tags("desktop");

test("should not allow edition of currency sign of monetary fields", async () => {
    await setupHTMLBuilder(
        `<span data-oe-model="product.template" data-oe-id="9" data-oe-field="list_price" data-oe-type="monetary" data-oe-expression="product.list_price">
            $&nbsp;<span class="oe_currency_value">750.00</span>
        </span>`
    );
    expect(":iframe span[data-oe-type]").toHaveProperty("isContentEditable", false);
    expect(":iframe span.oe_currency_value").toHaveProperty("isContentEditable", true);
});

test("clicking on the monetary field should select the amount", async () => {
    const { getEditor } = await setupHTMLBuilder(
        `<span data-oe-model="product.template" data-oe-id="9" data-oe-field="list_price" data-oe-type="monetary" data-oe-expression="product.list_price">
            $<span class="span-in-currency"/>&nbsp;<span class="oe_currency_value">750.00</span>
        </span>`
    );
    const editor = getEditor();
    await click(":iframe span.span-in-currency");
    expect(
        editor.shared.selection.areNodeContentsFullySelected(
            queryOne(":iframe span.oe_currency_value")
        )
    ).toBe(true, { message: "value of monetary field is selected" });
});
