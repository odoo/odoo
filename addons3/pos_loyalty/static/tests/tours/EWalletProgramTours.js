/** @odoo-module **/

import * as PosLoyalty from "@pos_loyalty/../tests/tours/PosLoyaltyTourMethods";
import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as TicketScreen from "@point_of_sale/../tests/tours/helpers/TicketScreenTourMethods";
import * as Chrome from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";
import * as PartnerListScreen from "@point_of_sale/../tests/tours/helpers/PartnerListScreenTourMethods";
import * as ErrorPopup from "@point_of_sale/../tests/tours/helpers/ErrorPopupTourMethods";
import { registry } from "@web/core/registry";

//#region EWalletProgramTour1
registry.category("web_tour.tours").add("EWalletProgramTour1", {
    test: true,
    url: "/pos/web",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickHomeCategory(),

            // Topup 50$ for partner_aaa
            ProductScreen.clickDisplayedProduct("Top-up eWallet"),
            PosLoyalty.orderTotalIs("50.00"),
            ProductScreen.clickPayButton(false),
            // If there's no partner, we asked to redirect to the partner list screen.
            Chrome.confirmPopup(),
            PartnerListScreen.isShown(),
            PartnerListScreen.clickPartner("AAAAAAA"),
            PosLoyalty.finalizeOrder("Cash", "50"),

            // Topup 10$ for partner_bbb
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("BBBBBBB"),
            ProductScreen.addOrderline("Top-up eWallet", "1", "10"),
            PosLoyalty.orderTotalIs("10.00"),
            PosLoyalty.finalizeOrder("Cash", "10"),
        ].flat(),
});
//#endregion
//#region EWalletProgramTour2
const getEWalletText = (suffix) => "eWallet" + (suffix !== "" ? ` ${suffix}` : "");
registry.category("web_tour.tours").add("EWalletProgramTour2", {
    test: true,
    url: "/pos/web",
    steps: () =>
        [
            ProductScreen.clickHomeCategory(),
            ProductScreen.addOrderline("Whiteboard Pen", "2", "6", "12.00"),
            PosLoyalty.eWalletButtonState({ highlighted: false }),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAAAAAA"),
            PosLoyalty.eWalletButtonState({ highlighted: true, text: getEWalletText("Pay") }),
            PosLoyalty.clickEWalletButton(getEWalletText("Pay")),
            PosLoyalty.orderTotalIs("0.00"),
            PosLoyalty.finalizeOrder("Cash", "0"),

            // Consume partner_bbb's full eWallet.
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("BBBBBBB"),
            PosLoyalty.eWalletButtonState({ highlighted: false }),
            ProductScreen.addOrderline("Desk Pad", "6", "6", "36.00"),
            PosLoyalty.eWalletButtonState({ highlighted: true, text: getEWalletText("Pay") }),
            PosLoyalty.clickEWalletButton(getEWalletText("Pay")),
            PosLoyalty.orderTotalIs("26.00"),
            PosLoyalty.finalizeOrder("Cash", "26"),

            // Switching partners should work.
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("BBBBBBB"),
            ProductScreen.addOrderline("Desk Pad", "2", "19", "38.00"),
            PosLoyalty.eWalletButtonState({ highlighted: false }),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAAAAAA"),
            PosLoyalty.eWalletButtonState({ highlighted: true, text: getEWalletText("Pay") }),
            PosLoyalty.clickEWalletButton(getEWalletText("Pay")),
            PosLoyalty.orderTotalIs("0.00"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("BBBBBBB"),
            PosLoyalty.eWalletButtonState({ highlighted: false }),
            PosLoyalty.orderTotalIs("38.00"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAAAAAA"),
            PosLoyalty.eWalletButtonState({ highlighted: true, text: getEWalletText("Pay") }),
            PosLoyalty.clickEWalletButton(getEWalletText("Pay")),
            PosLoyalty.orderTotalIs("0.00"),
            PosLoyalty.finalizeOrder("Cash", "0"),

            // Refund with eWallet.
            // - Make an order to refund.
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("BBBBBBB"),
            ProductScreen.addOrderline("Whiteboard Pen", "1", "20", "20.00"),
            PosLoyalty.orderTotalIs("20.00"),
            PosLoyalty.finalizeOrder("Cash", "20"),
            // - Refund order.
            ProductScreen.clickRefund(),
            TicketScreen.filterIs("Paid"),
            TicketScreen.selectOrder("-0004"),
            TicketScreen.partnerIs("BBBBBBB"),
            TicketScreen.confirmRefund(),
            ProductScreen.isShown(),
            PosLoyalty.eWalletButtonState({ highlighted: true, text: getEWalletText("Refund") }),
            PosLoyalty.clickEWalletButton(getEWalletText("Refund")),
            PosLoyalty.orderTotalIs("0.00"),
            PosLoyalty.finalizeOrder("Cash", "0"),
        ].flat(),
});

//#endregion

registry
    .category("web_tour.tours")
    .add('ExpiredEWalletProgramTour', {
        test: true,
        url: '/pos/ui',
        steps: () => [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickHomeCategory(),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer('AAAA'),
            ProductScreen.addOrderline('Whiteboard Pen', '2', '6', '12.00'),
            PosLoyalty.eWalletButtonState({ highlighted: false }),
            PosLoyalty.clickEWalletButton(),
            ErrorPopup.isShown(),
            ErrorPopup.clickConfirm()
        ].flat(),
});
