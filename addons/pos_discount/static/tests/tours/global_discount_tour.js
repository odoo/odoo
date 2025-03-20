import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("pos_global_discount_tax_group", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            ProductScreen.clickControlButton("Discount"),
            Dialog.confirm(),
            ProductScreen.totalAmountIs(90),
        ].flat(),
});

registry.category("web_tour.tours").add("pos_global_discount_tax_group_2", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            ProductScreen.clickControlButton("Discount"),
            Dialog.confirm(),
            ProductScreen.totalAmountIs(108),
        ].flat(),
});
