import { useService } from "@web/core/utils/hooks";
import { formatFloat } from "@web/views/fields/formatters";
import { Component, markup } from "@odoo/owl";
import { formatDate } from "@web/core/l10n/dates";

export class ForecastedHeader extends Component {
    static template = "stock.ForecastedHeader";
    static props = { docs: Object, openView: Function };

    setup(){
        this.orm = useService("orm");
        this.action = useService("action");
        this.tooltip = useService("tooltip");

        this._formatFloat = (num) => formatFloat(num, { digits: this.props.docs.precision });
    }

    async _onClickInventory(){
        const productIds = this.props.docs.product_variants_ids;
        const action = await this.orm.call('product.product', 'action_open_quants', [productIds]);
        if (action.help) {
            action.help = markup(action.help);
        }
        return this.action.doAction(action);
    }

    get products() {
        return this.props.docs.product;
    }

    get leadTime() {
        if (!this.products || this.products.length === 0) {
            return null;
        }
        const productsArray = Object.values(this.products || {});
        const product = productsArray.reduce((minProduct, p) => {
            if (
                !minProduct ||
                (p.leadtime && p.leadtime.total_delay < (minProduct.leadtime?.total_delay ?? Infinity))
            ) {
                return p;
            }
            return minProduct;
        }, null);
        const today = new luxon.DateTime.now();
        product.leadtime["today"] = formatDate(today);
        product.leadtime["earliestPossibleArrival"] = formatDate(
            today.plus({ days: product.leadtime.total_delay })
        );
        const details = product.leadtime.details;
        const discard = ["Time Horizon"];
        const reorder = [
            "Days to Purchase",
            "Order Deadline",
            "Vendor Lead Time",
            "Days to Supply Components",
            "Production Start Date",
            "Manufacturing Lead Time",
            "Production End Date",
            "Receipt Date",
            "Time Horizon",
        ].reverse();
        details.sort(
            (a, b) => reorder.findIndex((k) => k === b[0]) - reorder.findIndex((k) => k === a[0])
        );
        product.leadtime.details = details.filter((d) => !discard.includes(d[0]));
        return product.leadtime;
    }

    get leadTimeShort() {
        let short = " " + (this.leadTime.total_delay) + " day(s)";
        if (this.leadTime.total_delay != 0) {
            short += " (" + this.leadTime.earliestPossibleArrival + ")";
        }
        return short;
    }

    get quantityOnHand() {
        return Object.values(this.products).reduce((sum, product) => sum + product.quantity_on_hand, 0);
    }

    get incomingQty() {
        return Object.values(this.products).reduce((sum, product) => sum + product.incoming_qty, 0);
    }

    get outgoingQty() {
        return Object.values(this.products).reduce((sum, product) => sum + product.outgoing_qty, 0);
    }

    get virtualAvailable() {
        return Object.values(this.products).reduce((sum, product) => sum + product.virtual_available, 0);
    }

    get uom() {
        return Object.values(this.products)[0].uom;
    }

    toJsonString(obj) {
        return JSON.stringify(obj);
    }
}
