import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";

const formatters = registry.category("formatters");

/**
 * Custom list renderer for stock.move in the context of stock_account.
 *
 * The `quantity` and `value` fields are always stored as positive numbers.
 * This renderer overrides `computeAggregates` to produce a signed total at the
 * bottom of the list: outgoing moves (internal/transit → external) are counted
 * negatively, so the footer shows the net quantity/value (incoming − outgoing).
 */
export class StockMoveListRenderer extends ListRenderer {
    computeAggregates() {
        const aggregates = super.computeAggregates();

        // Signed recomputation only applies to the flat (non-grouped) list.
        // For grouped lists, server-side _read_group_postprocess_aggregate already
        // handles value:sum; quantity:sum from the server is intentionally left as-is.
        if (this.props.list.isGrouped) {
            return aggregates;
        }

        const records = this.props.list.selection.length
            ? this.props.list.selection
            : this.props.list.records;

        this._recomputeSignedAggregate(aggregates, records, "quantity");
        this._recomputeSignedAggregate(aggregates, records, "product_uom_qty");
        this._recomputeSignedAggregate(aggregates, records, "value");

        return aggregates;
    }

    _recomputeSignedAggregate(aggregates, records, fieldName) {
        if (!(fieldName in aggregates)) {
            return;
        }

        const column = this.columns.find((c) => c.type === "field" && c.name === fieldName);
        if (!column) {
            return;
        }

        const signedTotal = records.reduce((total, record) => {
            const { location_usage, location_dest_usage } = record.data;
            const isOut =
                ["internal", "transit"].includes(location_usage) &&
                !["internal", "transit"].includes(location_dest_usage);
            return total + (isOut ? -record.data[fieldName] : record.data[fieldName]);
        }, 0);

        const field = this.fields[fieldName];
        const formatter =
            formatters.get(column.widget, false) || formatters.get(field.type, false);
        const options = formatter?.extractOptions?.(column);
        const formatOptions = {
            ...options,
            digits: column.attrs.digits ? JSON.parse(column.attrs.digits) : undefined,
            escape: true,
        };

        aggregates[fieldName] = {
            ...aggregates[fieldName],
            rawValue: signedTotal,
            value: formatter ? formatter(signedTotal, formatOptions) : signedTotal,
        };
    }
}

export const stockAccountMoveListView = {
    ...listView,
    Renderer: StockMoveListRenderer,
};

registry.category("views").add("stock_account_move_list", stockAccountMoveListView);
