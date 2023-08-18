/** @odoo-module */

import { ProductCatalogSOL } from "@sale/js/product_catalog/sale_order_line/sale_order_line";
import { patch } from "@web/core/utils/patch";

patch(ProductCatalogSOL, {
    props: {
        ...ProductCatalogSOL.props,
        deliveredQty: Number,
    },
});
