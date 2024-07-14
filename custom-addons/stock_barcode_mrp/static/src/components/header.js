/** @odoo-module **/

import { Component } from "@odoo/owl";

export default class HeaderComponent extends Component {

    get order() {
        return this.env.model.record;
    }

    get qtyDemand() {
        return this.order.product_qty;
    }

    get incrementQty() {
        if (this.order.product_id.tracking == 'serial') {
            return this.order.qty_producing > 0 ? 0 : 1;
        }
        return Math.max(this.order.product_qty - this.order.qty_producing, 0);
    }

    get qtyDone() {
        return this.order.qty_producing;
    }

    get isTracked() {
        return this.order.product_id.tracking !== 'none';
    }

    get lotName() {
        return this.order.lot_producing_id?.name || this.order.lot_name || '';
    }

    get isComplete() {
        return this.env.model.isComplete;
    }

    get componentClasses() {
        return this.isComplete ? 'o_header_completed': '';
    }

    get hideProduceButton() {
        return this.incrementQty === 0;
    }

    get isSelected() {
        return true;
    }
}

HeaderComponent.props = ["displayUOM", "openDetails", "line"];
HeaderComponent.template = 'stock_barcode_mrp.HeaderComponent';
