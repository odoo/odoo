import * as PosLoyalty from "@pos_loyalty/../tests/tours/utils/pos_loyalty_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("ServiceFeeGiftCardSingleLineTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickDisplayedProduct("Item"),
            Order.hasServiceFee("5.00"), // 10% of 50.
            ProductScreen.totalAmountIs("55.00"),

            // A gift card is not something the fee is taken from. Its reward line
            // used to join that base and add a second fee line to the order.
            PosLoyalty.enterCode("GIFTCARD"),
            Dialog.proceed({ title: "unpaid gift card" }),
            Order.hasServiceFee("5.00"),
            ProductScreen.totalAmountIs("0.00"),
            Order.serviceFeeLineCountIs(1),
        ].flat(),
});

registry.category("web_tour.tours").add("ServiceFeeEWalletCoversFeeTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAAAAAA"),
            ProductScreen.clickDisplayedProduct("Item"),
            Order.hasServiceFee("5.00"), // 10% of 50.
            ProductScreen.totalAmountIs("55.00"),

            // An eWallet settles the whole bill, fee included: it pays 55, not the
            // 50 of products. It stays out of the base the fee is taken from, where
            // the fee would chase the payment down to nothing.
            PosLoyalty.eWalletButtonState({
                highlighted: true,
                text: "eWallet Pay",
                click: true,
            }),
            Order.hasLine({ productName: "eWallet", price: "-55.00" }),
            Order.hasServiceFee("5.00"),
            ProductScreen.totalAmountIs("0.00"),
            Order.serviceFeeLineCountIs(1),

            // Same after discount: an eWallet is a payment, not a discount.
            ProductScreen.selectPreset(
                "Percent 10 before discount",
                "Percent 10 after discount",
                false
            ),
            Order.hasLine({ productName: "eWallet", price: "-55.00" }),
            Order.hasServiceFee("5.00"),
            ProductScreen.totalAmountIs("0.00"),
            Order.serviceFeeLineCountIs(1),
        ].flat(),
});
