import { runAllTimers, test } from "@odoo/hoot";
import { definePosStockModels } from "@pos_stock/../tests/unit/data/generate_model_definitions";
import {
    setupCustomerDisplay,
    CustomerDisplayAssertions as Assert,
} from "@point_of_sale/../tests/unit/customer_display/utils";

definePosStockModels();

const addLots = (line, lotNames) =>
    line.editPackLotLines({
        modifiedPackLotLines: {},
        newPackLotLines: lotNames.map((lot_name) => ({ lot_name })),
    });

const hasLotName = async (productName, lotName) => {
    await runAllTimers();
    await Assert.waitAndExpect(
        `li.o_customer_display_orderline:has(.product-name:contains(${productName})):has(.info-list li:contains("${lotName}"))`
    );
};

test("customer display shows the lot/serial names of tracked product", async () => {
    const [store] = await setupCustomerDisplay();
    const line = await store.addLineToCurrentOrder({ product_tmpl_id: 5 });
    line.product_id.tracking = "lot";
    addLots(line, ["LOT001", "LOT002"]);

    await Assert.hasOrderLine({ productName: "TEST" });
    await hasLotName("TEST", "Lot LOT001");
    await hasLotName("TEST", "Lot LOT002");
});
