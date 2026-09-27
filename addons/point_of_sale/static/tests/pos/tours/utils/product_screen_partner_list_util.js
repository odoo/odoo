import * as PartnerList from "@point_of_sale/../tests/pos/tours/utils/partner_list_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import { back, selectButton } from "@point_of_sale/../tests/pos/tours/utils/common";

export function searchCustomerValueAndClear(val) {
    return [
        ProductScreen.clickPartnerButton(),
        PartnerList.searchCustomerValue(val),
        selectButton("Discard"),
        {
            isActive: ["mobile"],
            ...back(),
        },
    ].flat();
}
