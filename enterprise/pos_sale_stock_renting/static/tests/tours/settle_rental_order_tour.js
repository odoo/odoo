import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as PosSale from "@pos_sale/../tests/tours/utils/pos_sale_utils";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("OrderLotsRentalTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.settleNthOrder(1),
            ProductScreen.clickLotIcon(),
            ProductScreen.enterLotNumber("123456789"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});
