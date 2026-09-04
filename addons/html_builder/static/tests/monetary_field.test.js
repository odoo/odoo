import { setupHTMLBuilder } from "@html_builder/../tests/helpers";
import { BuilderContentEditablePlugin } from "@html_builder/core/builder_content_editable_plugin";
import { MonetaryFieldPlugin } from "@html_builder/plugins/monetary_field_plugin";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { expect, test, describe } from "@odoo/hoot";
import { click, queryOne } from "@odoo/hoot-dom";
import { testEditor } from "addons/html_editor/static/tests/_helpers/editor";
import { unformat } from "addons/html_editor/static/tests/_helpers/format";
import { deleteBackward } from "addons/html_editor/static/tests/_helpers/user_actions";

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

test("should make a span inside a monetary field be unremovable", async () => {
    await testEditor({
        contentBeforeEdit: unformat(`
                <p>
                    <span data-oe-model="product.template" data-oe-id="27" data-oe-field="list_price" data-oe-type="monetary" data-oe-expression="product.list_price" data-oe-xpath="/t[1]/div[1]/h3[2]/span[1]" class="o_editable">
                        $&nbsp;
                        <span class="oe_currency_value" data-oe-zws-empty-inline="">[]\u200b</span>
                    </span>
                </p>
            `),
        stepFunction: deleteBackward,
        contentAfter: unformat(`
                <p>
                    <span data-oe-model="product.template" data-oe-id="27" data-oe-field="list_price" data-oe-type="monetary" data-oe-expression="product.list_price" data-oe-xpath="/t[1]/div[1]/h3[2]/span[1]" class="o_editable">
                        $&nbsp;
                        <span class="oe_currency_value">[]</span>
                    </span>
                </p>
            `),
        config: {
            Plugins: [...MAIN_PLUGINS, MonetaryFieldPlugin, BuilderContentEditablePlugin],
        },
    });
});
