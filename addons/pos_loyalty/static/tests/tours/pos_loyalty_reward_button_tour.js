import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as PosLoyalty from "@pos_loyalty/../tests/tours/utils/pos_loyalty_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as SelectionPopup from "@point_of_sale/../tests/generic_helpers/selection_popup_util";
import { registry } from "@web/core/registry";
import * as ProductConfiguratorPopup from "@point_of_sale/../tests/pos/tours/utils/product_configurator_util";
import * as PartnerList from "@point_of_sale/../tests/pos/tours/utils/partner_list_util";

registry.category("web_tour.tours").add("test_loyalty_reward_with_variant", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            PartnerList.searchCustomerValue("Test Partner", true),
            ProductScreen.clickCustomer("Test Partner"),
            ProductScreen.clickDisplayedProduct("Test Product"),
            Dialog.discard(),
            ProductScreen.clickDisplayedProduct("Test Product"),
            ProductConfiguratorPopup.pickRadio("Value 1"),
            Dialog.confirm(),
            ProductScreen.clickDisplayedProduct("Test Product"),
            ProductConfiguratorPopup.pickRadio("Value 1"),
            Dialog.confirm(),
            ProductScreen.clickDisplayedProduct("Test Product"),
            ProductConfiguratorPopup.pickRadio("Value 1"),
            Dialog.confirm(),
            PosLoyalty.claimReward(
                'Add "Free Product - [Test Product (Value 1), Test Product (Value 2)]"'
            ),
            Dialog.is({ title: "Please select a product for this reward" }),
            SelectionPopup.has("Test Product (Value 1)", { run: "click" }),
            Dialog.isNot(),
            ProductScreen.selectedOrderlineHas(
                "Free Product - Test Product (Value 1)",
                "1",
                "0",
                "Value 1"
            ),
        ].flat(),
});
