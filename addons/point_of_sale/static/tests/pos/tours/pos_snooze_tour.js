import { registry } from "@web/core/registry";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ProductInfoScreen from "@point_of_sale/../tests/pos/tours/utils/product_info_screen_util";
import { scan_barcode } from "@point_of_sale/../tests/generic_helpers/utils";

registry.category("web_tour.tours").add("test_pos_snooze", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.longPressProduct("Desk Organizer"),
            ProductInfoScreen.productIsAvailable(),
            ProductInfoScreen.clickSnoozeButton(),
            ProductInfoScreen.clickSnoozeDuration("1 Hour"),
            Dialog.confirm("Apply"),
            ProductInfoScreen.productIsSnoozed(),
            Dialog.confirm("Close"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            Dialog.bodyIs("You are trying to add a snoozed product. Would you like to continue?"),
            Dialog.confirm("Continue"),
            ProductScreen.clickDisplayedProduct("Desk Organizer", true, 2),
            ProductScreen.longPressProduct("Desk Organizer"),
            ProductInfoScreen.clickSnoozeButton(),
            Dialog.confirm("Yes"),
            ProductInfoScreen.productIsAvailable(),
            Dialog.confirm("Close"),
            ProductScreen.clickDisplayedProduct("Desk Organizer", true, 3),
            ProductScreen.longPressProduct("Desk Organizer"),
            ProductInfoScreen.clickSnoozeButton(),
            ProductInfoScreen.clickSnoozeDuration("Session"),
            Dialog.confirm("Apply"),
            ProductInfoScreen.productIsSnoozed(),
            Dialog.confirm("Close"),
            Chrome.createFloatingOrder(),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            Dialog.bodyIs("You are trying to add a snoozed product. Would you like to continue?"),
            Dialog.confirm("Continue"),
            ProductScreen.clickDisplayedProduct("Desk Organizer", true, 2),
            Chrome.createFloatingOrder(),
            ProductScreen.longPressProduct("Monitor Stand"),
            ProductInfoScreen.productIsAvailable(),
            ProductInfoScreen.clickSnoozeButton(),
            ProductInfoScreen.clickSnoozeDuration("1 Hour"),
            Dialog.confirm("Apply"),
            ProductInfoScreen.productIsSnoozed(),
            Dialog.confirm("Close"),
            scan_barcode("0123456789"),
            Dialog.bodyIs("You are trying to add a snoozed product. Would you like to continue?"),
            Dialog.confirm("Continue"),
            scan_barcode("0123456789"),
            ProductScreen.selectedOrderlineHas("Monitor Stand", 2),
        ].flat(),
});
