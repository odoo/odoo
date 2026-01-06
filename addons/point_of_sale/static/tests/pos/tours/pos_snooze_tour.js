import { registry } from "@web/core/registry";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ProductInfoScreen from "@point_of_sale/../tests/pos/tours/utils/product_info_screen_util";

registry.category("web_tour.tours").add("test_pos_snooze", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickInfoProduct("Desk Organizer", [
                ProductInfoScreen.productIsAvailable(),
                ProductInfoScreen.clickSnoozeButton(),
                ProductInfoScreen.clickSnoozeDuration("1 Hour"),
                Dialog.confirm("Apply"),
                ProductInfoScreen.productIsSnoozed(),
                Dialog.confirm("Close"),
            ]),
            ProductScreen.productIsSnoozed("Desk Organizer"),
            ProductScreen.clickInfoProduct("Desk Organizer", [
                ProductInfoScreen.clickSnoozeButton(),
                Dialog.confirm("Yes"),
                ProductInfoScreen.productIsAvailable(),
                Dialog.confirm("Close"),
            ]),
            ProductScreen.productIsNotSnoozed("Desk Organizer"),
            ProductScreen.clickInfoProduct("Desk Organizer", [
                ProductInfoScreen.productIsAvailable(),
                ProductInfoScreen.clickSnoozeButton(),
                ProductInfoScreen.clickSnoozeDuration("Session"),
                Dialog.confirm("Apply"),
                ProductInfoScreen.productIsSnoozed(),
                Dialog.confirm("Close"),
            ]),
            ProductScreen.productIsSnoozed("Desk Organizer"),
        ].flat(),
});
