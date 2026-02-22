import { patch } from "@web/core/utils/patch";
import { ProductCatalogOrderLine } from "@product/product_catalog/order_line/order_line";

patch(ProductCatalogOrderLine, {
    props: {
        ...ProductCatalogOrderLine.props,
        min_qty: { type: Number, optional: true },
        packaging: { type: Object, optional: true },
    },
});
