import { expect, test, runAllTimers } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { defineModels, fields, models, mountView, onRpc } from "@web/../tests/web_test_helpers";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";

class ProductProduct extends models.Model {
    _name = "product.product";

    name = fields.Char({ string: "Product Name" });
    default_code = fields.Char({ string: "Default Code" });
    monthly_demand = fields.Float();
    suggested_qty = fields.Integer();

    _records = [
        { id: 1, name: "name1", default_code: "AAAA" },
        { id: 2, name: "name2", default_code: "AAAB", suggested_qty: 10 }, // suggested_qty to test display hiding on this record
        { id: 3, name: "name1", default_code: "AAAC" },
        { id: 4, name: "name2", default_code: "AAAD" },
    ];

    _views = {
        kanban: `
            <kanban records_draggable="0" js_class="purchase_product_kanban_catalog">
                <templates>
                    <t t-name="card">
                        <field name="name"/>
                        <field name="default_code"/>
                        <div name="o_kanban_price"
                        t-attf-id="product-{{record.id.raw_value}}-price"
                        class="d-flex flex-column"/>
                        <div name="kanban_purchase_suggest">
                            <!-- encapsulate in div with name="kanban_purchase_suggest" to make sure JS hides it -->
                            <field name="suggested_qty"/>
                        </div>
                    </t>
                </templates>
            </kanban>
        `,
    };
}

class PurchaseOrder extends models.Model {
    _name = "purchase.order";
    _records = [
        {
            id: 1,
        },
    ];
}

defineModels([ProductProduct, PurchaseOrder]);
defineMailModels();

const purchaseOrderLineInfo = {
    1: {
        quantity: 0,
        price: 35.0,
        uomDisplayName: "Units",
        min_qty: 1.0,
        suggested_qty: 0, // We will test adding without suggested qty works as expected
        productType: "consu",
    },
    2: {
        quantity: 0,
        price: 35.0,
        uomDisplayName: "Units",
        min_qty: 1.0,
        suggested_qty: 10, // We will test adding with suggested qty works as expected
        productType: "consu",
    },
    3: {
        quantity: 0,
        productType: "consu",
        uomDisplayName: "Units",
        price: 1299.0,
        min_qty: 5.0, // We will test adding with suggested qty < min_qty works as expected
        suggested_qty: 1,
    },
    4: {
        quantity: 0,
        productType: "consu",
        uomDisplayName: "Units",
        price: 1299.0,
        min_qty: 0.0, // We will test adding with min_qty = 0 works as expected (should add 1 not 0)
        suggested_qty: 1,
    },
};

onRpc("/product/catalog/order_lines_info", () => purchaseOrderLineInfo);

test("Adding products from purchase catalog with suggestion feature ON.", async () => {
    // Check that qty added from catalog record use the suggested ad min_qty field correctly
    // Also test that the field suggested_qty on the card is hidden if qty == suggested_qty

    onRpc("/product/catalog/update_order_line_info", async (request) => {
        const { params } = await request.json();
        const { product_id, quantity } = params;
        expect.step(`product_id=${product_id} quantity=${quantity}`);
        return {};
    });

    await mountView({
        resModel: "product.product",
        type: "kanban",
        context: {
            product_catalog_order_model: "purchase.order",
            order_id: 1,
        },
    });

    // ---- 1: Test adding product without suggested qty
    await click(".o_kanban_record:nth-of-type(1) button:has(i.fa-shopping-cart)");
    await runAllTimers(); // for skipping the debounce delay
    expect(".o_kanban_record:nth-of-type(1) .o_product_catalog_quantity .o_input").toHaveValue(1);

    // ---- 2: Test adding product with suggested qty
    expect(
        ".o_kanban_record:nth-of-type(2) div[name='kanban_purchase_suggest'] span:visible:contains('10')"
    ).toHaveCount(1, { message: "Suggested qty div should be visible on card #2" });
    await click(".o_kanban_record:nth-of-type(2) button:has(i.fa-shopping-cart)");
    await runAllTimers(); // for skipping the debounce delay
    expect(".o_kanban_record:nth-of-type(2) .o_product_catalog_quantity .o_input").toHaveValue(10);
    expect(
        ".o_kanban_record:nth-of-type(2) div[name='kanban_purchase_suggest'] span:visible:contains('10')"
    ).toHaveCount(0, { message: "Div should be invisible now that suggested_qty == qty" });

    // ---- 3: Test adding one more of product with suggested qty
    await click(".o_kanban_record:nth-of-type(2)");
    await runAllTimers(); // for skipping the debounce delay
    expect(".o_kanban_record:nth-of-type(2) .o_product_catalog_quantity .o_input").toHaveValue(11);
    expect(
        ".o_kanban_record:nth-of-type(2) div[name='kanban_purchase_suggest'] span:visible:contains('10')"
    ).toHaveCount(1, { message: "Suggested qty div should be visible again" });

    // ---- 4: Test adding product with suggested qty < min_qty
    await click(".o_kanban_record:nth-of-type(3)");
    await runAllTimers(); // for skipping the debounce delay
    expect(".o_kanban_record:nth-of-type(3) .o_product_catalog_quantity .o_input").toHaveValue(5); // Should use min_qty not suggested_qty

    // ---- 5: Test adding product with min_qty = 0
    await click(".o_kanban_record:nth-of-type(4)");
    await runAllTimers(); // for skipping the debounce delay
    expect(".o_kanban_record:nth-of-type(4) .o_product_catalog_quantity .o_input").toHaveValue(1); // Should add 1 not 0

    expect.verifySteps([
        "product_id=1 quantity=1",
        "product_id=2 quantity=10",
        "product_id=2 quantity=11",
        "product_id=3 quantity=5",
        "product_id=4 quantity=1",
    ]);
});
