import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as StockPaymentScreen from "@pos_stock/../tests/pos/tours/utils/payment_screen_util";
import { registry } from "@web/core/registry";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
import * as PartnerList from "@point_of_sale/../tests/pos/tours/utils/partner_list_util";

const { DateTime } = luxon;
const nextYear = DateTime.now().year + 1;

registry.category("web_tour.tours").add("test_pos_order_shipping_date", {
    steps: () =>
        [
            ProductScreen.setTimeZone("America/New_York"),
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Whiteboard Pen", "1"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            StockPaymentScreen.setShipLaterDate(""),
            StockPaymentScreen.setShipLaterDate(`${nextYear}-05-30`),
            PaymentScreen.clickValidate(),
            Dialog.discard(),
            PaymentScreen.clickValidate(),
            Dialog.confirm(),
            PartnerList.clickPartner("Partner Full"),
            FeedbackScreen.isShown(),
            FeedbackScreen.checkTicketData({
                is_shipping_date: true,
            }),
        ].flat(),
});
