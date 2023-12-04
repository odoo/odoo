/** @odoo-module */
import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as PaymentScreen from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import * as PosEvent from "@pos_event/../tests/PosEventTourMethods";
import * as Chrome from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosEventTour", {
    test: true,
    url: "/pos/ui",
    steps: () => [
        ProductScreen.confirmOpeningPopup(),
        ProductScreen.clickSubcategory("Events"),
        ProductScreen.clickDisplayedProduct("Conference for Architects TEST"),
        ProductScreen.addOrderline("Standard", "5"),
        ProductScreen.clickOrderline("Standard - Conference for Architects TEST", "5.0"),
        ProductScreen.selectedOrderlineHas("Standard - Conference for Architects TEST", "5.0"),
        PosEvent.productEventAvailableSeats("Standard", "95"),
        ProductScreen.clickPartnerButton(),
        ProductScreen.clickCustomer("A simple PoS man!"),
        ProductScreen.clickPayButton(),

        PaymentScreen.clickPaymentMethod('Cash'),
        PaymentScreen.remainingIs('0.00'),
        PaymentScreen.changeIs('0.0'),
        PaymentScreen.clickValidate(),

        ReceiptScreen.isShown(),

        Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("PartnerMandatory", {
    test: true,
    url: "/pos/ui",
    steps: () => [

        ProductScreen.confirmOpeningPopup(),
        ProductScreen.clickSubcategory("Events"),
        ProductScreen.clickDisplayedProduct("Conference for Architects TEST"),
        ProductScreen.clickDisplayedProduct("Standard"),
        ProductScreen.clickOrderline("Standard - Conference for Architects TEST", "1.0"),
        ProductScreen.clickPayButton(false),
        PosEvent.isShownCustomerNeeded(),

        Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("SoldoutTicket", {
    test: true,
    url: "/pos/ui",
    steps: () => [

        ProductScreen.confirmOpeningPopup(),
        ProductScreen.clickSubcategory("Events"),
        ProductScreen.clickDisplayedProduct("Conference for Architects TEST"),
        ProductScreen.clickDisplayedProduct("VIP"),
        ProductScreen.clickOrderline("VIP - Conference for Architects TEST", "1.0"),
        PosEvent.productEventAvailableSeats("VIP", "SOLD OUT"),
        ProductScreen.clickDisplayedProduct("VIP"),
        ProductScreen.clickOrderline("VIP - Conference for Architects TEST", "1.0"),

        Chrome.endTour(),
        ].flat(),
});
