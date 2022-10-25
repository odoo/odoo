/** @odoo-module */

import { registry } from "@web/core/registry";

const { Component } = owl;

export class StockQuantReserve extends Component {

    setup() {
        this.reserve_line_record = this.props.record;
        this.reserve_record = this.props.record.model.root;
    }

    async setToReserve() {
        const qty_to_reserve = Math.min(this.reserve_record.data.qty_to_reserve, this.reserve_line_record.data.available_quantity);
        await this.reserve_line_record.update({ qty_to_reserve });
    }
}

StockQuantReserve.template = "stock.StockQuantReserve";

const stockQuantReserve = {
    component: StockQuantReserve,
};

registry.category("view_widgets").add("stock_quant_reserve", stockQuantReserve);
