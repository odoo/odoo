import { useService } from "@web/core/utils/hooks";
import { formatFloat } from "@web/views/fields/formatters";
import { Component, markup } from "@odoo/owl";

export class ForecastedHeader extends Component {
    static template = "stock.ForecastedHeader";
    static props = { docs: Object, openView: Function, selectedWarehouseIds: Array };

    setup(){
        this.orm = useService("orm");
        this.action = useService("action");

        this._formatFloat = (num) => formatFloat(num, { digits: [0, this.props.docs.precision] });
    }

    async _onClickInventory(){
        const productIds = this.props.docs.product_variants_ids;
        const action = await this.orm.call('product.product', 'action_open_quants', [productIds]);
        action.domain = [
            ...(action.domain || []),
            ["warehouse_id", "in", this.props.selectedWarehouseIds],
        ];
        if (action.help) {
            action.help = markup(action.help);
        }
        return this.action.doAction(action);
    }

    async _onClickTransfers(type) {
        const action = await this.orm.call(
            "stock.picking",
            `get_action_picking_tree_${type === "incoming" ? "incoming" : "outgoing"}`
        );
        action.domain = [
            ["product_id", "in", this.props.docs.product_variants_ids],
            ["state", "not in", ["draft", "done", "cancel"]],
            ["picking_type_id.warehouse_id", "in", this.props.selectedWarehouseIds],
        ];
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
        const today = new Date(Date.now());
        product.leadtime["today"] = today.toLocaleDateString();
        product.leadtime["earliestPossibleArrival"] = this.addDays(today, product.leadtime.total_delay);
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

    addDays(date, days) {
        const result = new Date(date);
        result.setDate(result.getDate() + days);
        return result.toLocaleDateString();
    }

    toJsonString(obj) {
        return JSON.stringify(obj);
    }
}
