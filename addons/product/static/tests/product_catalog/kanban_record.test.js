import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { runAllTimers } from "@odoo/hoot-mock";
import {
    contains,
    defineModels,
    fields,
    makeServerError,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

class ProductProduct extends models.Model {
    _name = "product.product";

    name = fields.Char();

    _records = [{ id: 1, name: "Chair" }];
}

class SaleOrder extends models.Model {
    _name = "sale.order";

    state = fields.Char();

    _records = [{ id: 1, state: "sale" }];
}

defineModels([ProductProduct, SaleOrder]);
defineMailModels();

test("a failed quantity update does not block the next ones", async () => {
    onRpc("/product/catalog/order_lines_info", () => ({
        1: { price: 10, productType: "consu", quantity: 1 },
    }));
    let firstUpdate = true;
    onRpc("/product/catalog/update_order_line_info", async (request) => {
        const { params } = await request.json();
        expect.step(`update ${params.quantity}`);
        if (firstUpdate) {
            firstUpdate = false;
            throw makeServerError({ message: "It is forbidden to modify a locked order." });
        }
        return 10;
    });
    await mountView({
        arch: `
            <kanban js_class="product_kanban_catalog">
                <templates>
                    <t t-name="card">
                        <field name="name"/>
                        <div t-attf-id="product-{{record.id.raw_value}}-price"/>
                    </t>
                </templates>
            </kanban>`,
        context: { order_id: 1, product_catalog_order_model: "sale.order" },
        resModel: "product.product",
        type: "kanban",
    });
    expect.errors(1);
    await contains(".o_product_catalog_quantity button:has(.fa-plus)").click();
    await runAllTimers();
    await expect.waitForSteps(["update 2"]);
    await expect.waitForErrors(["It is forbidden to modify a locked order."]);
    await contains(".modal .btn-primary").click();
    await contains(".o_product_catalog_quantity button:has(.fa-plus)").click();
    await runAllTimers();
    await expect.waitForSteps(["update 3"]);
});
