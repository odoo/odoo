/* global posmodel */
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_sync_from_ui_one_by_one", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            {
                trigger: "body",
                content: "Create fake orders",
                run: async () => {
                    // Create 5 orders that will be synced one by one
                    for (let i = 0; i < 5; i++) {
                        const product = posmodel.models["product.product"].find(
                            (el) => el.attribute_line_ids.length == 0
                        );
                        const order = posmodel.createNewOrder();
                        await posmodel.addLineToOrder({ product_id: product }, order);
                        posmodel.addPendingOrder([order.id]);
                    }
                },
            },
            // Create one more order to be able to trigger the sync from the UI
            ProductScreen.clickDisplayedProduct("Desk Pad"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});
