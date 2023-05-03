/** @odoo-module */

import { Component } from "@odoo/owl";

export class Table extends Component {
    static template = "pos_restaurant.Table";
    static props = {
        onClick: Function,
        table: {
            type: Object,
            shape: {
                position_h: Number,
                position_v: Number,
                width: Number,
                height: Number,
                shape: String,
                color: [String, { value: false }],
                name: String,
                seats: Number,
                "*": true,
            },
        },
    };

    get style() {
        const table = this.props.table;

        if (this.env.pos.floorPlanStyle == "kanban") {
            const floor = table.floor;
            const index = floor.tables.indexOf(table);
            const minWidth = 100 + 20;
            const nbrHorizontal = Math.floor(window.innerWidth / minWidth);
            const widthTable = (window.innerWidth - nbrHorizontal*10) / nbrHorizontal;
            const position_h = widthTable * (index % nbrHorizontal) + 5 + (index % nbrHorizontal) * 10;
            const position_v = widthTable * Math.floor(index / nbrHorizontal) + 5 + Math.floor(index / nbrHorizontal) * 10;
            return `
                width: ${widthTable}px;
                height: ${widthTable}px;
                line-height: ${widthTable}px;
                top: ${position_v}px;
                left: ${position_h}px;
                border-radius: ${table.shape === "round" ? 1000 : 3}px;
                background: ${table.color || "rgb(53, 211, 116)"};
                font-size: ${widthTable >= 150 ? 32 : 16}px;
            `;
        } else {
            return `
                width: ${table.width}px;
                height: ${table.height}px;
                line-height: ${table.height}px;
                top: ${table.position_v}px;
                left: ${table.position_h}px;
                border-radius: ${table.shape === "round" ? 1000 : 3}px;
                background: ${table.color || "rgb(53, 211, 116)"};
                font-size: ${table.height >= 150 && table.width >= 150 ? 32 : 16}px;
            `;
        }
    }
    get fill() {
        const customerCount = this.env.pos.getCustomerCount(this.props.table.id);
        return Math.min(1, Math.max(0, customerCount / this.props.table.seats));
    }
    get orderCount() {
        const table = this.props.table;
        return table.order_count !== undefined
            ? table.order_count
            : this.env.pos
                  .getTableOrders(table.id)
                  .filter((o) => o.orderlines.length !== 0 || o.paymentlines.length !== 0).length;
    }
    get orderCountClass() {
        const countClass = { "order-count": true };
        if (this.env.pos.orderPreparationCategories.size) {
            const notifications = this._getNotifications();
            countClass["notify-printing"] = notifications.printing;
            countClass["notify-skipped"] = notifications.skipped;
        }
        return countClass;
    }
    get customerCountDisplay() {
        return `${this.env.pos.getCustomerCount(this.props.table.id)}/${this.props.table.seats}`;
    }
    _getNotifications() {
        const orders = this.env.pos.getTableOrders(this.props.table.id);

        let hasChangesCount = 0;
        let hasSkippedCount = 0;
        for (let i = 0; i < orders.length; i++) {
            if (orders[i].hasChangesToPrint()) {
                hasChangesCount++;
            } else if (orders[i].hasSkippedChanges()) {
                hasSkippedCount++;
            }
        }

        return hasChangesCount ? { printing: true } : hasSkippedCount ? { skipped: true } : {};
    }
}
