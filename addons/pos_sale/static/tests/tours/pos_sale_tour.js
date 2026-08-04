import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PosSale from "@pos_sale/../tests/tours/utils/pos_sale_utils";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("POSSalePaymentScreenInvoiceOrder", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Product Test", "1"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAA - Test Partner invoice"),
            ProductScreen.clickPayButton(),

            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            Chrome.waitRequest(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_sale_order_fp_different_from_partner_one", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.settleSaleOrderByPrice("20.00"),
            ProductScreen.checkTaxAmount("10.00"),
            ProductScreen.checkFiscalPosition("Partner FP"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.clickNextOrder(),
            PosSale.settleSaleOrderByPrice("10.00"),
            ProductScreen.checkTaxAmount("0.00"),
            ProductScreen.checkFiscalPosition("Sale Order FP"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.clickNextOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("PoSApplyDownpaymentWithExtraLine", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.downPaymentFirstOrder("+10"),
            ProductScreen.clickDisplayedProduct("product_a"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_variant_popup_qty_free", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Color Product"),
            {
                content: "Click on Inventory",
                trigger: 'button.accordion-header:contains("Inventory")',
                run: "click",
            },
            {
                content: "Check the variant's qty",
                trigger:
                    'div:not(:has(div)):contains("available,"):has(span.fw-bolder:contains("0"):not(:contains("50")))',
            },
            Dialog.confirm("Add"),
        ].flat(),
});
