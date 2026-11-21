import { ListRenderer } from "@web/views/list/list_renderer";
import { formatMonetary } from "@web/views/fields/formatters";

export class SaleReportListRenderer extends ListRenderer {
    /**
     * Weight the unit price average by the ordered quantity
     */
    computeAggregates() {
        const aggregates = super.computeAggregates();
        if (!aggregates.price_unit) {
            return aggregates;
        }
        const list = this.props.list;
        let values;
        if (list.selection.length) {
            values = list.selection.map((r) => r.data);
        } else if (list.isGrouped) {
            values = list.groups.map((g) => g.aggregates);
        } else {
            values = list.records.map((r) => r.data);
        }
        let totalPrice = 0;
        for (const { price_unit, product_uom_qty } of values) {
            totalPrice += (price_unit || 0) * (product_uom_qty || 0);
        }
        const totalQty = aggregates.product_uom_qty?.rawValue || 0;
        if (!totalQty) {
            return aggregates;
        }
        const rawValue = totalPrice / totalQty;
        const currencyId =
            list.isGrouped && !list.selection.length
                ? values.find((v) => v.currency_id?.length)?.currency_id[0]
                : values[0].currency_id?.id;
        aggregates.price_unit = {
            ...aggregates.price_unit,
            rawValue,
            value: formatMonetary(rawValue, { currencyId }),
        };
        return aggregates;
    }
}
