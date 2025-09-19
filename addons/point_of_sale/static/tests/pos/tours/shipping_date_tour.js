import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import { registry } from "@web/core/registry";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
import * as PartnerList from "@point_of_sale/../tests/pos/tours/utils/partner_list_util";

registry.category("web_tour.tours").add("test_pos_order_shipping_date", {
    steps: () =>
        [
            ProductScreen.setTimeZone("America/New_York"),
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Whiteboard Pen", "1"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            {
                content: "click ship later button",
                trigger: ".button:contains('Ship Later')",
                run: "click",
            },
            {
                content: "pick a date",
                trigger: ".modal-body .o_datetime_input",
                run: () => {
                    const input = document.querySelector(".modal-body .o_datetime_input");
                    const nextYear = new Date().getFullYear() + 1;
                    input.value = `${nextYear}-05-30`;
                    input.dispatchEvent(new Event("input", { bubbles: true }));
                    input.dispatchEvent(new Event("change", { bubbles: true }));
                },
            },
            {
                content: "click confirm button",
                trigger: ".btn:contains('Confirm')",
                run: "click",
            },
            {
                content: "Assert shipping date was set",
                trigger: ".payment-buttons .d-flex .btn span",
                run: () => {
                    const spans = [
                        ...document.querySelectorAll(".payment-buttons .d-flex .btn span"),
                    ];
                    const nextYear = new Date().getFullYear() + 1;
                    const expectedDate = `5/30/${nextYear}`;
                    if (!spans.some((span) => span.innerText === expectedDate)) {
                        throw new Error("Expected shipping date is not set");
                    }
                },
            },
            PaymentScreen.clickValidate(),
            Dialog.confirm(),
            PartnerList.clickPartner("Partner Test with Address"),
            FeedbackScreen.isShown(),
            FeedbackScreen.checkTicketData({
                is_shipping_date: true,
            }),
        ].flat(),
});
