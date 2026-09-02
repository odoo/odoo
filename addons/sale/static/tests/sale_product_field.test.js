import { expect, test } from "@odoo/hoot";
import { press, runAllTimers } from "@odoo/hoot-dom";
import {
    Command,
    contains,
    defineModels,
    fields,
    makeMockServer,
    models,
    mountView,
    onRpc,
    patchWithCleanup,
    serverState,
} from "@web/../tests/web_test_helpers";
import { saleModels } from "./sale_test_helpers";
import { SaleOrderLineProductField } from "@sale/js/sale_product_field/sale_product_field";

class SaleOrderLine extends saleModels.SaleOrderLine {
    product_template_attribute_value_ids = fields.Many2many({
        string: "Product template attributes values",
        relation: "product.template.attribute.value",
    });
}

class ProductTemplateAttributeValue extends models.Model {
    _name = "product.template.attribute.value";

    name = fields.Char();
}

defineModels({ ...saleModels, SaleOrderLine, ProductTemplateAttributeValue });

saleModels.SaleOrder._views.form = /* xml */ `
    <form>
        <field name="order_line" widget="sol_o2m" mode="list">
            <list editable="bottom">
                <field name="product_id" widget="sol_product_many2one"/>
                <field name="product_template_id" widget="sol_product_many2one"/>
                <field name="name" widget="sol_label_text"/>
            </list>
        </field>
    </form>
`;

test.tags("desktop");
test("pressing tab with incomplete text will create a product", async () => {
    onRpc(({ method }) => {
        expect.step(method);
    });
    await mountView({
        type: "form",
        resModel: "sale.order",
        arch: `
                <form>
                    <sheet>
                        <field name="order_line">
                            <list editable="bottom">
                                <field name="product_template_id" widget="sol_product_many2one"/>
                                <field name="product_id" optional="hide"/>
                                <field name="name" optional="show"/>
                            </list>
                        </field>
                    </sheet>
                </form>`,
    });

    patchWithCleanup(SaleOrderLineProductField.prototype, {
        async _getProductConfiguratorData() {
            expect.step("_getProductConfiguratorData");
            return {
                product_id: { id: 42, display_name: "Test Product" },
                product_name: "Test Product",
            };
        },
    });

    // add a line and enter new product name
    await contains(".o_field_x2many_list .o_field_x2many_list_row_add button").click();
    await contains("[name='product_template_id'] input").edit("new product");
    await press("tab");
    await runAllTimers();
    expect.verifySteps([
        "get_views",
        "onchange",
        "onchange",
        "web_name_search",
        "name_create",
        "_getProductConfiguratorData",
    ]);
});
