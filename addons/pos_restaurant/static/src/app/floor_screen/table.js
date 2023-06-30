/** @odoo-module */

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";

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

    setup() {
        this.pos = usePos();
    }
    get style() {
        const table = this.props.table;

        let background = table.color ? table.color : "rgb(53, 211, 116)";
        let textColor = "white";
        let border = "auto";
        let boxShadow = "0px 3px rgba(0,0,0,0.07)";
        if (!this.isOccupied()) {
            background = "transparent";
            const rgb = table.floor.background_color
                .substring(4, table.floor.background_color.length - 1)
                .replace(/ /g, "")
                .split(",");
            textColor =
                (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255 > 0.5 ? "black" : "white";
            border = "3px solid " + table.color;
            boxShadow = "none";
        }

        if (this.pos.floorPlanStyle == "kanban") {
            const floor = table.floor;
            const index = floor.tables.indexOf(table);
            const minWidth = 100 + 20;
            const nbrHorizontal = Math.floor(window.innerWidth / minWidth);
            const widthTable = (window.innerWidth - nbrHorizontal * 10) / nbrHorizontal;
            const position_h =
                widthTable * (index % nbrHorizontal) + 5 + (index % nbrHorizontal) * 10;
            const position_v =
                widthTable * Math.floor(index / nbrHorizontal) +
                5 +
                Math.floor(index / nbrHorizontal) * 10;
            return `
                width: ${widthTable}px;
                height: ${widthTable}px;
                line-height: ${widthTable}px;
                top: ${position_v}px;
                left: ${position_h}px;
                border: ${border};
                border-radius: ${table.shape === "round" ? 1000 : 3}px;
                background: ${background};
                box-shadow: ${boxShadow};
                font-size: ${widthTable >= 150 ? 32 : 16}px;
                color: ${textColor};
            `;
        } else {
            return `
                width: ${table.width}px;
                height: ${table.height}px;
                line-height: ${table.height}px;
                top: ${table.position_v}px;
                left: ${table.position_h}px;
                border: ${border};
                border-radius: ${table.shape === "round" ? 1000 : 3}px;
                background: ${background};
                box-shadow: ${boxShadow};
                font-size: ${table.height >= 150 && table.width >= 150 ? 32 : 16}px;
                color: ${textColor};
            `;
        }
    }
    get fill() {
        const customerCount = this.pos.getCustomerCount(this.props.table.id);
        return Math.min(1, Math.max(0, customerCount / this.props.table.seats));
    }
    get orderCount() {
        const table = this.props.table;
        const unsynced_orders = this.pos.getTableOrders(table.id).filter(
            (o) =>
                o.server_id === undefined &&
                (o.orderlines.length !== 0 || o.paymentlines.length !== 0) &&
                // do not count the orders that are already finalized
                !o.finalized
        );
        let result;
        if (table.changes_count > 0) {
            result = table.changes_count;
        } else if (table.skip_changes > 0) {
            result = table.skip_changes;
        } else {
            result = table.order_count + unsynced_orders.length;
        }
        return !Number.isNaN(result) ? result : 0;
    }
    get orderCountClass() {
        const countClass = { "order-count": true };
        if (this.pos.orderPreparationCategories.size) {
            const notifications = this._getNotifications();
            countClass["notify-printing"] = notifications.printing;
            countClass["notify-skipped"] = notifications.skipped;
        }
        return countClass;
    }
    get customerCountDisplay() {
        return `${this.pos.getCustomerCount(this.props.table.id)}/${
            this.props.table.seats
        }`;
    }
    _getNotifications() {
        const table = this.props.table;

        const hasChangesCount = table.changes_count;
        const hasSkippedCount = table.skip_changes;

        return hasChangesCount ? { printing: true } : hasSkippedCount ? { skipped: true } : {};
    }
    isOccupied() {
        return (
            this.pos.getCustomerCount(this.props.table.id) > 0 ||
            this.props.table.order_count > 0
        );
    }
}
