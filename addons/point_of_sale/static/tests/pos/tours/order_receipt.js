/* global posmodel */
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_receipt_data", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.orderIsEmpty(),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Example Partner"),
            ProductScreen.clickDisplayedProduct("Example Simple Product"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true),
            {
                content: "Throw receipt data to check in backend",
                trigger: "body",
                run: async () => {
                    const order = posmodel.getOrder();
                    order.setOrderPrices();
                    order.state = "paid";
                    await posmodel.syncAllOrders({ orders: [order] });
                    const generator = posmodel.getOrderReceiptGenerator(order);
                    const html = await generator.generateHtml();

                    if (!html.innerHTML.includes("This is a test header for receipt")) {
                        throw new Error("Receipt header not found in generated HTML");
                    }
                    if (!html.innerHTML.includes("This is a test footer for receipt")) {
                        throw new Error("Receipt footer not found in generated HTML");
                    }

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
