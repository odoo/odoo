import * as PosHr from "@pos_hr/../tests/tours/utils/pos_hr_helpers";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as CashierSelectionPopup from "@pos_hr/../tests/tours/utils/cashier_selection_popup_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import { registry } from "@web/core/registry";

function openRegisterAsBasicCashier() {
    return [
        Chrome.clickBtn("Open Register"),
        PosHr.loginScreenIsShown(),
        PosHr.clickLoginButton(),
        CashierSelectionPopup.has("Test Employee 3", { run: "click" }),
        Dialog.confirm("Open Register"),
        ProductScreen.isShown(),
    ];
}

function submitVoidPopup({ reason, passcode, confirmLabel }) {
    return [
        {
            trigger: ".modal:has(#l10n_ph_void_reason)",
        },
        {
            trigger: "#l10n_ph_void_reason",
            run: `edit ${reason}`,
        },
        ...(passcode !== undefined
            ? [
                  {
                      trigger: "#l10n_ph_void_passcode",
                      run: `edit ${passcode}`,
                  },
              ]
            : []),
        {
            trigger: `.modal-footer button:contains("${confirmLabel}")`,
            run: "click",
        },
    ];
}

registry.category("web_tour.tours").add("L10nPhPosCashierCanClose", {
    steps: () =>
        [
            Chrome.clickBtn("Open Register"),
            PosHr.loginScreenIsShown(),
            PosHr.clickLoginButton(),
            CashierSelectionPopup.has("Test Employee 3", { run: "click" }),
            Dialog.confirm("Open Register"),
            Chrome.clickMenuOption("Close Register"),
            Dialog.is("Closing Register"),
            Dialog.discard({ title: "Closing Register" }),
        ].flat(),
});

registry.category("web_tour.tours").add("L10nPhPosLineVoidFlow", {
    steps: () =>
        [
            ...openRegisterAsBasicCashier(),
            ProductScreen.addOrderline("Desk Pad", "1"),
            ProductScreen.clickNumpad("Qty", "0"),
            ...submitVoidPopup({
                reason: "Tour line void",
                passcode: "2580",
                confirmLabel: "Confirm Void",
            }),
            ...ProductScreen.orderIsEmpty(),
        ].flat(),
});

registry.category("web_tour.tours").add("L10nPhPosQuantityDecreaseFlow", {
    steps: () =>
        [
            ...openRegisterAsBasicCashier(),
            ProductScreen.addOrderline("Desk Pad", "2"),
            ProductScreen.clickNumpad("Qty", "1"),
            ProductScreen.clickNumpad("Qty"),
            ...submitVoidPopup({
                reason: "Tour quantity decrease",
                passcode: "2580",
                confirmLabel: "Approve Change",
            }),
            ProductScreen.orderLineHas("Desk Pad", "1"),
        ].flat(),
});

registry.category("web_tour.tours").add("L10nPhPosInvalidPasscodeFlow", {
    steps: () =>
        [
            ...openRegisterAsBasicCashier(),
            ProductScreen.addOrderline("Desk Pad", "1"),
            ProductScreen.clickNumpad("Qty", "0"),
            ...submitVoidPopup({
                reason: "Tour invalid passcode",
                passcode: "0000",
                confirmLabel: "Confirm Void",
            }),
            Dialog.is({ title: "Unable to save audit action" }),
            Dialog.confirm(),
            ProductScreen.orderLineHas("Desk Pad", "1"),
        ].flat(),
});

registry.category("web_tour.tours").add("L10nPhPosBypassLineVoidFlow", {
    steps: () =>
        [
            ...openRegisterAsBasicCashier(),
            ProductScreen.addOrderline("Desk Pad", "2"),
            ProductScreen.clickNumpad("Qty", "1"),
            ProductScreen.clickNumpad("Qty"), // commit
            ...submitVoidPopup({
                reason: "Self approved quantity decrease",
                confirmLabel: "Approve Change",
            }),
            ProductScreen.orderLineHas("Desk Pad", "1"),
            ProductScreen.clickNumpad("0"),
            ...submitVoidPopup({
                reason: "Self approved line void",
                confirmLabel: "Confirm Void",
            }),
            ...ProductScreen.orderIsEmpty(),
        ].flat(),
});

registry.category("web_tour.tours").add("L10nPhPosCancelLineVoidFlow", {
    steps: () =>
        [
            ...openRegisterAsBasicCashier(),
            ProductScreen.addOrderline("Desk Pad", "2"),
            ProductScreen.clickNumpad("Qty", "1"),
            ProductScreen.clickNumpad("Qty"),
            { trigger: ".modal:has(#l10n_ph_void_reason)" },
            Dialog.discard(),
            ProductScreen.orderLineHas("Desk Pad", "2"),
        ].flat(),
});

registry.category("web_tour.tours").add("L10nPhPosMultiDigitDecreaseFlow", {
    steps: () =>
        [
            ...openRegisterAsBasicCashier(),
            ProductScreen.addOrderline("Desk Pad", "30"),
            ProductScreen.clickNumpad("Qty", "2", "5"),
            ProductScreen.clickNumpad("Qty"),
            ...submitVoidPopup({
                reason: "Multi-digit decrease",
                passcode: "2580",
                confirmLabel: "Approve Change",
            }),
            ProductScreen.orderLineHas("Desk Pad", "25"),
        ].flat(),
});
