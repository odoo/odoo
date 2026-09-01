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

registry.category("web_tour.tours").add("test_pos_settle_pre_paid_so", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.checkOrdersListEmpty(),
            PosSale.removeUnpaidFilter(),
            PosSale.isOrdersListNotEmpty(),
            {
                content: "Select paid sale order",
                trigger: `.modal:not(.o_inactive_modal) table.o_list_table tbody tr.o_data_row td:contains('partner_a')`,
                run: "click",
            },
            ProductScreen.totalAmountIs("1,150.00"),
            ProductScreen.clickPayButton(),
            // Kept the payment name dynamic as this tour is reused across tests;
            // the actual payment is either PBNK1/2007/00001 or PBNK1/2007/00002.
            {
                trigger: ["00001", "00002"]
                    .map((sequence) =>
                        PaymentScreen._getPaymentlineSelector({
                            name: `Online Payment: PBNK1/2007/${sequence}`,
                            amount: "1,150.00",
                        })
                    )
                    .join(", "),
            },
            PaymentScreen.clickValidate(),
            FeedbackScreen.clickNextOrder(),
            PosSale.checkOrdersListEmpty(),
        ].flat(),
});
