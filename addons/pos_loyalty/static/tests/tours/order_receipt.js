/* global posmodel */
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as PosLoyalty from "@pos_loyalty/../tests/tours/utils/pos_loyalty_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_receipt_data_pos_loyalty", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Example Simple Product", "4"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Example Partner"),
            PosLoyalty.claimReward("Free Product - Example Simple Product"),
            PosLoyalty.hasRewardLine("Free Product - Example Simple Product", "-5.80", "1"),
            PosLoyalty.orderTotalIs("23.20"),
            PosLoyalty.finalizeOrder("Cash", "23.20"),
            Chrome.isSynced(),
            {
                content: "Throw receipt data to check in backend",
                trigger: "body",
                run: async () => {
                    const order = posmodel.models["pos.order"].find((o) => o.finalized);
                    await posmodel.postProcessLoyalty(order);
                    const generator = posmodel.getOrderReceiptGenerator(order);
                    const data = generator.generateData();
                    try {
                        await posmodel.data.call("pos.order", "get_order_frontend_receipt_data", [
                            [order.id],
                            data,
                        ]);
                    } finally {
                        // Ignore any error, the main test is in the backend
                    }
                },
            },
        ].flat(),
});
