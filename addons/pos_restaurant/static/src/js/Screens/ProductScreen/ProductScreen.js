/** @odoo-module */

import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { patch } from "@web/core/utils/patch";

patch(ProductScreen, "pos_restaurant.ProductScreen", {
    showBackToFloorButton: true,
});
