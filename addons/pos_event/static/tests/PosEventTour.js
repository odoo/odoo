/** @odoo-module */
import { ProductScreen } from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import { PaymentScreen } from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import { ReceiptScreen } from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import { PosEvent } from "@pos_event/../tests/PosEventTourMethods";
import { getSteps, startSteps } from "@point_of_sale/../tests/tours/helpers/utils";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosEventTour", {
    test: true,
    url: "/pos/ui",
    steps: () => {
        startSteps();

        ProductScreen.do.confirmOpeningPopup();
        ProductScreen.do.clickSubcategory("Events");
        ProductScreen.do.clickDisplayedProduct("Conference for Architects TEST");
        ProductScreen.exec.addOrderline("Standard", "5");
        ProductScreen.do.clickOrderline("Standard - Conference for Architects TEST", "5.0");
        ProductScreen.check.selectedOrderlineHas("Standard - Conference for Architects TEST", "5.0");
        PosEvent.check.productEventAvailableSeats("Standard", "95");
        ProductScreen.do.clickPartnerButton();
        ProductScreen.do.clickCustomer("A simple PoS man!");
        ProductScreen.do.clickPayButton();

        PaymentScreen.do.clickPaymentMethod('Cash');
        PaymentScreen.check.remainingIs('0.00');
        PaymentScreen.check.changeIs('0.0');
        PaymentScreen.do.clickValidate();

        ReceiptScreen.check.isShown();
        return getSteps();
    }
});

registry.category("web_tour.tours").add("PartnerMandatory", {
    test: true,
    url: "/pos/ui",
    steps: () => {
        startSteps();

        ProductScreen.do.confirmOpeningPopup();
        ProductScreen.do.clickSubcategory("Events");
        ProductScreen.do.clickDisplayedProduct("Conference for Architects TEST");
        ProductScreen.do.clickDisplayedProduct("Standard");
        ProductScreen.do.clickOrderline("Standard - Conference for Architects TEST", "1.0");
        ProductScreen.do.clickPayButton(false);
        PosEvent.check.isShownCustomerNeeded();

        return getSteps();
    }
});

registry.category("web_tour.tours").add("SoldoutTicket", {
    test: true,
    url: "/pos/ui",
    steps: () => {
        startSteps();

        ProductScreen.do.confirmOpeningPopup();
        ProductScreen.do.clickSubcategory("Events");
        ProductScreen.do.clickDisplayedProduct("Conference for Architects TEST");
        ProductScreen.do.clickDisplayedProduct("VIP");
        ProductScreen.do.clickOrderline("VIP - Conference for Architects TEST", "1.0");
        PosEvent.check.productEventAvailableSeats("VIP", "SOLD OUT");
        ProductScreen.do.clickDisplayedProduct("VIP");
        ProductScreen.do.clickOrderline("VIP - Conference for Architects TEST", "1.0");

        return getSteps();
    }
});
