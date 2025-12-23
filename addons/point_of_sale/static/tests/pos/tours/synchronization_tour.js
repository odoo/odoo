/* global posmodel */

import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
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
<<<<<<< babd9219dc387fe47ce7d1f37cadb0adeed789b7:addons/point_of_sale/static/tests/pos/tours/synchronization_tour.js
                        const product = posmodel.models["product.template"].find(
                            (p) => p.name === "Desk Pad"
                        );
||||||| bb82c24295ae582053a2e46a6c5a3cd9358c5e86:addons/point_of_sale/static/tests/tours/synchronization_tour.js
                        const product = posmodel.models["product.product"].getFirst();
=======
                        const product = posmodel.models["product.product"].find(
                            (el) => el.attribute_line_ids.length == 0
                        );
>>>>>>> 1359a89250dbd81530d390a2c0da90621b30240d:addons/point_of_sale/static/tests/tours/synchronization_tour.js
                        const order = posmodel.createNewOrder();
                        await posmodel.addLineToOrder({ product_tmpl_id: product }, order);
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
