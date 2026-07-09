import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("l10n_pk_edi_pos_discount_disabled_tour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickControlButtonMore(),
            {
                content: "The Discount button is out of reach: the FBR cannot report one",
                trigger: ".control-buttons button.js_discount[disabled]",
            },
        ].flat(),
});
