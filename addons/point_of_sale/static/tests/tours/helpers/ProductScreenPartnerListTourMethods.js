/** @odoo-module */

import * as PartnerList from "@point_of_sale/../tests/tours/helpers/PartnerListTourMethods";
import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import { selectButton } from "@point_of_sale/../tests/tours/helpers/utils";

export function searchCustomerValueAndClear(val) {
    return [
        ProductScreen.clickPartnerButton(),
        PartnerList.searchCustomerValue(val),
        selectButton("Ok"),
        ProductScreen.goBackToMainScreen(),
    ].flat();
}
