/** @odoo-module */

import { Component, useState } from "@odoo/owl";
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
        this.state = useState({
            containerHeight: 0,
            containerWidth: 0,
        });
    }
    get fontSize() {
        const size = this.state.containerHeight / 3;
        return size > 20 ? 20 : size;
    }
    get badgeStyle() {
        if (this.props.table.shape !== "round") {
            return `top: -6px; right: -6px;`;
        }

        const tableHeight = this.state.containerHeight;
        const tableWidth = this.state.containerWidth;
        const radius = Math.min(tableWidth, tableHeight) / 2;

        let left = 0;
        let bottom = 0;

        if (tableHeight > tableWidth) {
            left = radius;
            bottom = radius + (tableHeight - tableWidth);
        } else {
            bottom = radius;
            left = radius + (tableWidth - tableHeight);
        }

        bottom += 0.7 * radius - 8;
        left += 0.7 * radius - 8;

        return `bottom: ${bottom}px; left: ${left}px;`;
    }
    computePosition(index, nbrHorizontal, widthTable) {
        const position_h = widthTable * (index % nbrHorizontal) + 5 + (index % nbrHorizontal) * 10;
        const position_v =
            widthTable * Math.floor(index / nbrHorizontal) +
            10 +
            Math.floor(index / nbrHorizontal) * 10;
        return { position_h, position_v };
    }
    get style() {
        const table = this.props.table;
        let style = "";
        let background = table.color ? table.color : "rgb(53, 211, 116)";
        let textColor = "white";

        if (!this.isOccupied()) {
            background = "#00000020";
            const rgb = table.floor.background_color
                .substring(4, table.floor.background_color.length - 1)
                .replace(/ /g, "")
                .split(",");
            textColor =
                (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255 > 0.5 ? "black" : "white";
        }

        style += `
            border: 3px solid ${table.color};
            border-radius: ${table.shape === "round" ? 1000 : 3}px;
            background: ${background};
            box-shadow: 0px 3px rgba(0,0,0,0.07);
            padding: ${table.shape === "round" ? "4px 10px" : "4px 8px"};
            color: ${textColor};`;

        if (this.pos.floorPlanStyle == "kanban") {
            const floor = table.floor;
            const index = floor.tables.indexOf(table);
            const minWidth = 120;
            const nbrHorizontal = Math.floor(window.innerWidth / minWidth);
            const widthTable = (window.innerWidth - nbrHorizontal * 10) / nbrHorizontal;
            const { position_h, position_v } = this.computePosition(
                index,
                nbrHorizontal,
                widthTable
            );

            this.state.containerHeight = widthTable;
            this.state.containerWidth = widthTable;

            style += `
                width: ${widthTable}px;
                height: ${widthTable}px;
                top: ${position_v}px;
                left: ${position_h}px;
            `;
        } else {
            this.state.containerHeight = table.height;
            this.state.containerWidth = table.width;

            style += `
                width: ${table.width}px;
                height: ${table.height}px;
                top: ${table.position_v}px;
                left: ${table.position_h}px;
            `;
        }

        style += `
            font-size: ${this.fontSize}px;
            line-height: ${this.fontSize}px;`;

        return style;
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
        const notifications = this._getNotifications();
        const countClass = {
            "order-count": true,
            "notify-printing text-bg-danger": notifications.printing,
            "notify-skipped text-bg-info": notifications.skipped,
            "text-bg-dark": !notifications.printing && !notifications.skipped,
        };
        return countClass;
    }
    get customerCountDisplay() {
        const customerCount = this.pos.getCustomerCount(this.props.table.id);
        if (customerCount == 0) {
            return `${this.props.table.seats}`;
        } else {
            return `${customerCount}/${this.props.table.seats}`;
        }
    }
    _getNotifications() {
        const table = this.props.table;

        const hasChangesCount = table.changes_count;
        const hasSkippedCount = table.skip_changes;

        return hasChangesCount ? { printing: true } : hasSkippedCount ? { skipped: true } : {};
    }
    isOccupied() {
        return (
            this.pos.getCustomerCount(this.props.table.id) > 0 || this.props.table.order_count > 0
        );
    }
}
