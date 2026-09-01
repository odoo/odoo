import * as PosLoyalty from "@pos_loyalty/../tests/tours/utils/pos_loyalty_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as SelectionPopup from "@point_of_sale/../tests/generic_helpers/selection_popup_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import { negate } from "@point_of_sale/../tests/generic_helpers/utils";
import { registry } from "@web/core/registry";

const getEWalletText = (suffix) => "eWallet" + (suffix !== "" ? ` ${suffix}` : "");
registry.category("web_tour.tours").add("MultipleGiftWalletProgramsTour", {
    steps: () =>
        [
            // One card for gift_card_1.
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Gift Card"),
            SelectionPopup.has("gift_card_1"),
            SelectionPopup.has("gift_card_2"),
            SelectionPopup.has("gift_card_1", { run: "click" }),
            ProductScreen.selectedOrderlineHas("Gift Card"),
            ProductScreen.clickNumpad("Price"),
            ProductScreen.modeIsActive("Price"),
            ProductScreen.clickNumpad("1", "0"),
            PosLoyalty.orderTotalIs("10.00"),
            PosLoyalty.finalizeOrder("Cash", "10"),
            // One card for gift_card_1.
            ProductScreen.clickDisplayedProduct("Gift Card"),
            SelectionPopup.has("gift_card_2", { run: "click" }),
            ProductScreen.selectedOrderlineHas("Gift Card"),
            ProductScreen.clickNumpad("Price"),
            ProductScreen.modeIsActive("Price"),
            ProductScreen.clickNumpad("2", "0"),
            PosLoyalty.orderTotalIs("20.00"),
            PosLoyalty.finalizeOrder("Cash", "20"),
            ProductScreen.clickDisplayedProduct("Gift Card"),
            SelectionPopup.has("gift_card_1"),
            SelectionPopup.has("gift_card_2", { run: "click" }),
            PosLoyalty.createManualGiftCard("physical-gift-card-2", "15"),
            {
                content: "the program selection popup is not shown a second time",
                trigger: negate(".selection-item"),
            },
            ProductScreen.selectedOrderlineHas("Gift Card", "1", "15"),
            PosLoyalty.orderTotalIs("15.00"),
            PosLoyalty.finalizeOrder("Cash", "15"),
            // Top up ewallet_1 for AAAAAAA.
            ProductScreen.clickDisplayedProduct("Top-up eWallet"),
            SelectionPopup.has("ewallet_1"),
            SelectionPopup.has("ewallet_2"),
            SelectionPopup.has("ewallet_1", { run: "click" }),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAAAAAA"),
            ProductScreen.clickNumpad("Price"),
            ProductScreen.modeIsActive("Price"),
            ProductScreen.clickNumpad("3", "0"),
            PosLoyalty.orderTotalIs("30.00"),
            PosLoyalty.finalizeOrder("Cash", "30"),
            // Top up ewallet_2 for AAAAAAA.
            ProductScreen.clickDisplayedProduct("Top-up eWallet"),
            SelectionPopup.has("ewallet_2", { run: "click" }),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAAAAAA"),
            ProductScreen.clickNumpad("Price"),
            ProductScreen.modeIsActive("Price"),
            ProductScreen.clickNumpad("4", "0"),
            PosLoyalty.orderTotalIs("40.00"),
            PosLoyalty.finalizeOrder("Cash", "40"),
            // Top up ewallet_1 for BBBBBBB.
            ProductScreen.clickDisplayedProduct("Top-up eWallet"),
            SelectionPopup.has("ewallet_1", { run: "click" }),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("BBBBBBB"),
            PosLoyalty.orderTotalIs("50.00"),
            PosLoyalty.finalizeOrder("Cash", "50"),
            // Consume 12$ from ewallet_1 of AAAAAAA.
            ProductScreen.addOrderline("Whiteboard Pen", "2", "6", "12.00"),
            PosLoyalty.eWalletButtonState({ highlighted: false }),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAAAAAA"),
            PosLoyalty.eWalletButtonState({
                highlighted: true,
                text: getEWalletText("Pay"),
                click: true,
            }),
            SelectionPopup.has("ewallet_1"),
            SelectionPopup.has("ewallet_2"),
            SelectionPopup.has("ewallet_1", { run: "click" }),
            PosLoyalty.orderTotalIs("0.00"),
            PosLoyalty.finalizeOrder("Cash", "0"),
        ].flat(),
});
