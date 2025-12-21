import * as PosHr from "@pos_hr/../tests/tours/utils/pos_hr_helpers";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as SelectionPopup from "@point_of_sale/../tests/generic_helpers/selection_popup_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_post_login_default_screen_is_tables", {
    steps: () =>
        [
            Chrome.clickBtn("Open Register"),
            PosHr.clickLoginButton(),
            SelectionPopup.has("Mitchell Admin", { run: "click" }),
            Dialog.confirm("Open Register"),
            FloorScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_post_login_default_screen_is_register", {
    steps: () =>
        [
            Chrome.clickBtn("Open Register"),
            PosHr.clickLoginButton(),
            SelectionPopup.has("Mitchell Admin", { run: "click" }),
            Dialog.confirm("Open Register"),
            ProductScreen.isShown(),
        ].flat(),
});
