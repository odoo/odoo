import { ProductCatalogOrderLine } from "@product/product_catalog/order_line/order_line";
import { formatDuration } from "@web/core/l10n/dates";

export class ProductCatalogSaleOrder extends ProductCatalogOrderLine {
    static template = "sale.ProductCatalogSaleOrderLine";
    static props = {
        ...ProductCatalogOrderLine.props,
        last_invoice_date: { type: 'datetime', optional: true },
    }

    get invoice_date() {
        const duration = (new Date() - new Date(this.props.last_invoice_date)) / 1000
        if ((duration / (24 * 3600)) > 1) {
            return formatDuration(duration, false);
        }
        return '0d';
    }
}
