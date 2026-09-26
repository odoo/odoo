import { test, expect } from "@odoo/hoot";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosStockModels } from "../data/generate_model_definitions";

definePosStockModels();

test("price of lot tracked product with and without pricelist", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    await mountWithCleanup(ProductScreen, { props: { orderUuid: order.uuid } });

    const lotProduct = store.models["product.template"].get(41);
    order.pricelist_id = store.models["product.pricelist"].get(21);

    const addLotProduct = async (lot) => {
        const addLinePromise = store.addLineToOrder(
            {
                product_tmpl_id: lotProduct,
                qty: 1,
            },
            order
        );
        // this closes "Server Communication Problem" dialog
        await contains("button:contains(Yes)").click();

        await contains(".modal-dialog input.o-autocomplete--input.o_input").edit(lot);
        await contains("button:contains(Apply)").click();
        await addLinePromise;
    };

    await addLotProduct("1");
    order.setOrderPrices();
    expect(order.lines.length).toBe(1);
    expect(order.lines[0].qty).toBe(1);
    expect(order.amount_total).toBe(30);

    await addLotProduct("2");
    order.setOrderPrices();
    expect(order.lines.length).toBe(1);
    expect(order.lines[0].qty).toBe(2);
    expect(order.amount_total).toBe(40);

    order.pricelist_id = false;
    await addLotProduct("3");
    order.setOrderPrices();
    expect(order.lines.length).toBe(2);
    expect(order.lines[0].qty).toBe(2);
    expect(order.lines[1].qty).toBe(1);
    expect(order.amount_total).toBe(30);
});
