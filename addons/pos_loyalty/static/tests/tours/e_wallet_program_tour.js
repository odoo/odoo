import * as PosLoyalty from "@pos_loyalty/../tests/tours/utils/pos_loyalty_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/tours/utils/ticket_screen_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as PartnerList from "@point_of_sale/../tests/tours/utils/partner_list_util";
import * as Numpad from "@point_of_sale/../tests/tours/utils/numpad_util";
import * as Order from "@point_of_sale/../tests/tours/utils/generic_components/order_widget_util";
import { negateStep } from "@point_of_sale/../tests/tours/utils/common";
import { delay } from "@web/core/utils/concurrency";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("EWalletProgramTour1", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Topup 50$ for partner_aaa
            ProductScreen.clickDisplayedProduct("Top-up eWallet"),
            PosLoyalty.orderTotalIs("50.00"),
            ProductScreen.clickPayButton(false),
            // If there's no partner, we asked to redirect to the partner list screen.
            Dialog.confirm(),
            PartnerList.clickPartner("AAAAAAA"),
            PosLoyalty.finalizeOrder("Cash", "50"),

            // Topup 10$ for partner_bbb
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("BBBBBBB"),
            ProductScreen.addOrderline("Top-up eWallet", "1", "10"),
            PosLoyalty.orderTotalIs("10.00"),
            PosLoyalty.finalizeOrder("Cash", "10"),

            // Check numpad visibility when clicking on eWallet orderline
            ProductScreen.addOrderline("Whiteboard Pen"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAAAAAA"),
            PosLoyalty.eWalletButtonState({
                highlighted: true,
                text: getEWalletText("Pay"),
                click: true,
            }),
            PosLoyalty.orderTotalIs("0.00"),
            ...ProductScreen.clickLine("eWallet"),
            // Added a small wait because the clickLine function uses a 300ms timeout
            {
                content: "Wait 300ms after clicking orderline",
                trigger: "body",
                async run() {
                    await delay(300);
                },
            },
            Numpad.isVisible(),
            ...Order.hasLine({
                withClass: ".selected",
                run: "click",
                productName: "eWallet",
                quantity: "1.0",
            }),
            {
                content: "Wait 300ms after clicking orderline",
                trigger: "body",
                async run() {
                    await delay(300);
                },
            },
            negateStep(Numpad.isVisible()),
            {
                content: "Click Current Balance line in orderline",
                trigger: ".orderline li:contains(Current Balance:)",
                run: "click",
            },
            Numpad.isVisible(),
        ].flat(),
});

const getEWalletText = (suffix) => "eWallet" + (suffix !== "" ? ` ${suffix}` : "");
registry.category("web_tour.tours").add("EWalletProgramTour2", {
    steps: () =>
        [
            Chrome.startPoS(),
            ProductScreen.addOrderline("Whiteboard Pen", "2", "6", "12.00"),
            PosLoyalty.eWalletButtonState({ highlighted: false }),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAAAAAA"),
            PosLoyalty.eWalletButtonState({
                highlighted: true,
                text: getEWalletText("Pay"),
                click: true,
            }),
            PosLoyalty.orderTotalIs("0.00"),
            PosLoyalty.finalizeOrder("Cash", "0"),

            // Consume partner_bbb's full eWallet.
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("BBBBBBB"),
            PosLoyalty.eWalletButtonState({ highlighted: false }),
            ProductScreen.addOrderline("Desk Pad", "6", "6", "36.00"),
            PosLoyalty.eWalletButtonState({
                highlighted: true,
                text: getEWalletText("Pay"),
                click: true,
            }),
            PosLoyalty.eWalletButtonState({ highlighted: false }),
            PosLoyalty.orderTotalIs("26.00"),
            PosLoyalty.finalizeOrder("Cash", "26"),

            // Switching partners should work.
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("BBBBBBB"),
            ProductScreen.addOrderline("Desk Pad", "2", "19", "38.00"),
            PosLoyalty.eWalletButtonState({ highlighted: false }),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAAAAAA"),
            PosLoyalty.eWalletButtonState({
                highlighted: true,
                text: getEWalletText("Pay"),
                click: true,
            }),
            PosLoyalty.orderTotalIs("0.00"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("BBBBBBB"),
            PosLoyalty.eWalletButtonState({ highlighted: false }),
            PosLoyalty.orderTotalIs("38.00"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAAAAAA"),
            PosLoyalty.eWalletButtonState({
                highlighted: true,
                text: getEWalletText("Pay"),
                click: true,
            }),
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
            ...ProductScreen.clickRefund(),
            TicketScreen.filterIs("Paid"),
            TicketScreen.selectOrder("-0004"),
            TicketScreen.confirmRefund(),
            ProductScreen.isShown(),
            PosLoyalty.eWalletButtonState({
                highlighted: true,
                text: getEWalletText("Refund"),
                click: true,
            }),
            PosLoyalty.orderTotalIs("0.00"),
            PosLoyalty.finalizeOrder("Cash", "0"),
        ].flat(),
});

registry.category("web_tour.tours").add("ExpiredEWalletProgramTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAAA"),
            ProductScreen.addOrderline("Whiteboard Pen", "2", "6", "12.00"),
            PosLoyalty.eWalletButtonState({ highlighted: false, click: true }),
            Dialog.is({ title: "No valid eWallet found" }),
            Dialog.confirm(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyPointsEwallet", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAAA"),
            PosLoyalty.eWalletButtonState({ highlighted: false }),
            ProductScreen.addOrderline("product_a", "1"),
            PosLoyalty.eWalletButtonState({
                highlighted: true,
                text: getEWalletText("Pay"),
                click: true,
            }),
            PosLoyalty.pointsAwardedAre("100"),
            PosLoyalty.finalizeOrder("Cash", "90.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("EWalletLoyaltyHistory", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickDisplayedProduct("Top-up eWallet"),
            PosLoyalty.orderTotalIs("50.00"),
            ProductScreen.clickPartnerButton(),
            PartnerList.clickPartner("AAAAAAA"),
            PosLoyalty.finalizeOrder("Cash", "50"),

            ProductScreen.addOrderline("Whiteboard Pen", "2", "6", "12.00"),
            PosLoyalty.eWalletButtonState({ highlighted: false }),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAAAAAA"),
            PosLoyalty.eWalletButtonState({
                highlighted: true,
                text: getEWalletText("Pay"),
                click: true,
            }),
            PosLoyalty.orderTotalIs("0.00"),
            PosLoyalty.finalizeOrder("Cash", "0"),
        ].flat(),
});
