/** @odoo-module */

import { Component, useRef } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { getLimits, useMovable, constrain } from "@point_of_sale/app/utils/movable_hook";

const MIN_TABLE_SIZE = 30; // px

export class Table extends Component {
    static template = "pos_restaurant.Table";
    static props = {
        onClick: Function,
        selectedTables: Array,
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
        class: { type: String, optional: true },
        style: { type: String, optional: true },
        limit: { type: Object, optional: true },
    };
    static defaultProps = {
        class: "",
        style: "",
    };

    setup() {
        this.pos = usePos();
        this.root = useRef("root");
        this.handles = {
            "top left": ["minX", "minY"],
            "top right": ["maxX", "minY"],
            "bottom left": ["minX", "maxY"],
            "bottom right": ["maxX", "maxY"],
        };
        // make table draggable
        useMovable({
            ref: this.root,
            onMoveStart: () => this.onMoveStart(),
            onMove: ({ dx, dy }) => {
                if (this.isKanban()) {
                    return;
                }
                const { minX, minY, maxX, maxY } = getLimits(this.root.el, this.props.limit.el);
                for (const [index, table] of Object.entries(this.selectedTablesCopy)) {
                    this.props.selectedTables[index].position_h = constrain(
                        table.position_h + dx,
                        minX,
                        maxX
                    );
                    this.props.selectedTables[index].position_v = constrain(
                        table.position_v + dy,
                        minY,
                        maxY
                    );
                }
            },
        });
        // make table resizable
        for (const [handle, toMove] of Object.entries(this.handles)) {
            useMovable({
                ref: useRef(handle),
                onMoveStart: () => this.onMoveStart(),
                onMove: (delta) => this.onResizeHandleMove(toMove, delta),
            });
        }
    }
    isKanban() {
        return this.pos.floorPlanStyle === "kanban";
    }
    get badgeStyle() {
        if (this.props.table.shape !== "round" || this.isKanban()) {
            return `top: -6px; right: -6px;`;
        }
        const tableHeight = this.props.table.height;
        const tableWidth = this.props.table.width;
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
    get tNotif() {
        return this.pos.tableNotifications[this.props.table.id];
    }
    get orderCount() {
        const tNotif = this.tNotif;
        if (!tNotif) {
            return 0;
        }
        if (tNotif.changes_count > 0) {
            return tNotif.changes_count;
        }
        if (tNotif.skip_changes > 0) {
            return tNotif.skip_changes;
        }
        const unsynced_orders = this.pos.getTableOrders(this.props.table.id).filter(
            (o) =>
                o.server_id === undefined &&
                (o.orderlines.length !== 0 || o.paymentlines.length !== 0) &&
                // do not count the orders that are already finalized
                !o.finalized
        );
        return tNotif.order_count + unsynced_orders.length || 0;
    }
    onMoveStart() {
        if (this.isKanban()) {
            return;
        }
        this.startTable = { ...this.props.table };
        this.selectedTablesCopy = {};
        for (let i = 0; i < this.props.selectedTables.length; i++) {
            this.selectedTablesCopy[i] = { ...this.props.selectedTables[i] };
        }
    }
    onResizeHandleMove([moveX, moveY], { dx, dy }) {
        if (this.isKanban()) {
            return;
        }
        // Working with min/max x and y makes constraints much easier to apply uniformly
        const { width, height, position_h: minX, position_v: minY } = this.startTable;
        const newTable = { minX, minY, maxX: minX + width, maxY: minY + height };

        const limits = getLimits(this.root.el, this.props.limit.el);
        const { width: elWidth, height: elHeight } = this.root.el.getBoundingClientRect();
        const bounds = {
            maxX: [minX + MIN_TABLE_SIZE, limits.maxX + elWidth],
            minX: [limits.minX, newTable.maxX - MIN_TABLE_SIZE],
            maxY: [minY + MIN_TABLE_SIZE, limits.maxY + elHeight],
            minY: [limits.minY, newTable.maxY - MIN_TABLE_SIZE],
        };
        newTable[moveX] = constrain(newTable[moveX] + dx, ...bounds[moveX]);
        newTable[moveY] = constrain(newTable[moveY] + dy, ...bounds[moveY]);

        // Convert back to server format at the end
        this.props.table.position_h = newTable.minX;
        this.props.table.position_v = newTable.minY;
        this.props.table.width = newTable.maxX - newTable.minX;
        this.props.table.height = newTable.maxY - newTable.minY;
    }
    /**
     * Offsets the resize handles from the edge of the table. For square tables,
     * the offset is half the width of the handle (we just want a quarter circle
     * to be visible), for round tables it's half the width plus the distance of
     * the middle of the rounded border's arc to the edge.
     *
     * @param {`${'top'|'bottom'} ${'left'|'right'}`} handleName the handle for
     *  which to compute the style
     * @returns {string} the value of the style attribute for the given handle
     */
    computeHandleStyle(handleName) {
        const table = this.props.table;
        // 24 is half the handle's width
        let offset = -24;
        if (table.shape === "round") {
            // min(width/2, height/2) is the real border radius
            // 0.2929 is (1 - cos(45°)) to get in the middle of the border's arc
            offset += Math.min(table.width / 2, table.height / 2) * 0.2929;
        }
        return handleName
            .split(" ")
            .map((dir) => `${dir}: ${offset}px;`)
            .join(" ");
    }
}
