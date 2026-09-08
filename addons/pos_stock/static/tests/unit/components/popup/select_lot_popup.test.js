import { expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { onRpc, mountWithCleanup, contains } from "@web/../tests/web_test_helpers";
import { setupPosEnv, dialogActions } from "@point_of_sale/../tests/unit/utils";
import { definePosStockModels } from "../../data/generate_model_definitions";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";

definePosStockModels();

test("lot popup creates lot on apply", async () => {
    onRpc("pos.order.line", "get_existing_lots", () => []);

    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const product = store.models["product.template"].get(5);
    const line = await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);
    product.tracking = "lot";
    line.product_id.tracking = "lot";

    expect(line.qty).toBe(1);
    expect(line.hasValidProductLot()).toBe(false);

    await mountWithCleanup(OrderSummary, { props: {} });
    await dialogActions(
        () => click(".line-lot-icon"),
        [
            () => contains(".o-autocomplete--input").edit("LOT1", { confirm: false }),
            () => click(".modal-footer .btn-primary"),
        ]
    );
    expect(line.pack_lot_ids.map((lot) => lot.lot_name)).toEqual(["LOT1"]);
    expect(line.hasValidProductLot()).toBe(true);
    expect(line.qty).toBe(1);

    await dialogActions(
        () => click(".line-lot-icon"),
        [
            () => contains(".o-autocomplete--input").edit("", { confirm: false }),
            () => click(".modal-footer .btn-primary"),
        ]
    );
    expect(line.pack_lot_ids.length).toBe(0);
    expect(line.hasValidProductLot()).toBe(false);
    expect(line.qty).toBe(1);
});
