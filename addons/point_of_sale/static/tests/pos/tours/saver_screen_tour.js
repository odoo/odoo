/* global posmodel */
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import { negate } from "@point_of_sale/../tests/generic_helpers/utils";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("SaverScreenCloseOverlaysTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.is({ title: "Opening Control" }),

            // Test Dialog Overlay Close
            {
                trigger: "body",
                run: () => posmodel.showScreen("SaverScreen"),
            },
            Dialog.isNot(),

            // Dismiss the SaverScreen
            {
                trigger: "body",
                run: () => posmodel.showScreen("LoginScreen"),
            },
            // Click the open register button on the login screen to enter the store
            {
                trigger: ".screen-login .btn.open-register-btn",
                run: "click",
            },
            Dialog.confirm("Open Register"),

            // Test Popover Overlay Close
            Chrome.clickMenuButton(),
            {
                trigger: "body",
                run: () => posmodel.showScreen("SaverScreen"),
            },
            {
                trigger: negate(".dropdown-menu"),
            },
        ].flat(),
});
