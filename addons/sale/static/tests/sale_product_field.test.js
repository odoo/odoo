import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { press, runAllTimers } from "@odoo/hoot-dom";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

class SaleOrder extends models.Model {
    _name = "sale.order";

    name = fields.Char();
    order_line = fields.One2many({
        relation: "sale.order.line",
        relation_field: "order_id",
    });

    _records = [
        {
            id: 1,
            name: "first record",
            order_line: [],
        },
    ];
}

class SaleOrderLine extends models.Model {
    _name = "sale.order.line";

    order_id = fields.Many2one({
        string: "Order Reference",
        relation: "sale.order",
        relation_field: "order_line",
    });
    product_template_id = fields.Many2one({
        string: "Product",
        relation: "product.template",
    });
    product_id = fields.Many2one({
        string: "Product",
        relation: "product.product",
    });
    name = fields.Char();
    product_type = fields.Selection({
        selection: [],
    });
    service_tracking = fields.Selection({
        selection: [],
    });
    is_configurable_product = fields.Boolean({
        string: "Is product configurable",
    });
    product_template_attribute_value_ids = fields.Many2many({
        string: "Product template attributes values",
        relation: "product.template.attribute.value",
    });
    // added to the field dependencies by sale_product_matrix module
    product_add_mode = fields.Selection({
        selection: [],
    });
}

class ProductTemplate extends models.Model {
    _name = "product.template";

    name = fields.Char();
    get_single_product_variant() {
        return { product_id: 14, product_name: "desk" };
    }

    _records = [{ id: 12, name: "desk" }];
}

class ProductTemplateAttributeValue extends models.Model {
    _name = "product.template.attribute.value";

    name = fields.Char();
}

class Product extends models.Model {
    _name = "product.product";

    name = fields.Char();

    _records = [{ id: 14, name: "desk" }];
}

defineModels([SaleOrder, SaleOrderLine, ProductTemplate, ProductTemplateAttributeValue, Product]);
defineMailModels();

test.tags`desktop`;
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

    // add a line and enter new product name
    await contains(".o_field_x2many_list .o_field_x2many_list_row_add a").click();
    await contains("[name='product_template_id'] input").edit("new product");
    await press("tab");
    await runAllTimers();
    expect.verifySteps([
        "get_views",
        "onchange",
        "onchange",
        "web_name_search",
        "name_create",
        "get_single_product_variant",
    ]);
});
