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
        ].flat(),
});
