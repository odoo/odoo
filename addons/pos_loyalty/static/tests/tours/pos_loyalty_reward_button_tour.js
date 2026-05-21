import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as PosLoyalty from "@pos_loyalty/../tests/tours/utils/pos_loyalty_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
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
            PosLoyalty.hasRewardLine("Free Product", "-10", "1.00"),
        ].flat(),
});
