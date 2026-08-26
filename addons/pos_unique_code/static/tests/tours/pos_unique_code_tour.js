import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as UniqueCode from "@pos_unique_code/../tests/helpers/unique_code_popup_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_pos_unique_code", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // A used code is refused, a free one lets the order through.
            ProductScreen.addOrderline("Desk Pad", "1"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            // Typed on the keyboard: the digits must land in the popup, not in the
            // payment screen behind it.
            UniqueCode.typeCode("22222"),
            UniqueCode.codeIs("22222"),
            UniqueCode.confirm(),
            UniqueCode.isRejected("This code has already been used"),
            // Tapped on the numpad: the refused code is dropped on the first tap.
            UniqueCode.enterCode("11111"),
            UniqueCode.codeIs("11111"),
            UniqueCode.confirm(),
            FeedbackScreen.isShown(),
            FeedbackScreen.clickNextOrder(),

            // The cashier can validate without a code.
            ProductScreen.addOrderline("Desk Pad", "1"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            UniqueCode.forceValidate(),
            FeedbackScreen.isShown(),
        ].flat(),
});
