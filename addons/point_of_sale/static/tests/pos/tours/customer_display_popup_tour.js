import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("customer_display_shows_qr_popup", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            Chrome.waitForMenuButtons(),
            Chrome.clickMenuButton(),
            Chrome.waitForMenuOptionsToOpen(),
            Chrome.ClickOnCustomerDisplayButton(),
            Chrome.CustomerDisplayHasThisDeviceButton(),
            Chrome.CustomerDisplayHasQRButton(),
            Chrome.ClickCustomerDisplayQRButton(),
            Chrome.CustomerDisplayQRIsDisplayed(),
            {
                isActive: ["mobile"],
                content: "Check that the Customer display url is valid",
                trigger: ".o-overlay-item .modal .modal-body .small a",
                run: function (el) {
                    const url = el.anchor.href;
                    if (!url || url.includes("undefined")) {
                        throw new Error(
                            `Invalid customer display URL (contains undefined): ${url}`
                        );
                    }
                    try {
                        new URL(url);
                    } catch {
                        throw new Error(`Invalid customer display URL: ${url}`);
                    }
                },
            },
            {
                isActive: ["mobile"],
                content: "Check that the Qr popup has close button",
                trigger: ".o-overlay-item .modal .modal-body button.button.btn-secondary",
            },
        ].flat(),
});
