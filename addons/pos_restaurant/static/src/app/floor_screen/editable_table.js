/** @odoo-module */

import { getLimits, useMovable, constrain } from "@point_of_sale/app/movable_hook";
import { onWillUnmount, useEffect, useRef, Component } from "@odoo/owl";
import { Table } from "./table";

const MIN_TABLE_SIZE = 30; // px

export class EditableTable extends Component {
    static template = "pos_restaurant.EditableTable";
    static props = {
        onSaveTable: Function,
        limit: { type: Object, shape: { el: [HTMLElement, { value: null }] } },
        table: Table.props.table,
    };

    setup() {
        super.setup();
        useEffect(this._setElementStyle.bind(this));
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
            onMove: (delta) => this.onMove(delta),
        });
        // make table resizable
        for (const [handle, toMove] of Object.entries(this.handles)) {
            useMovable({
                ref: useRef(handle),
                onMoveStart: () => this.onMoveStart(),
                onMove: (delta) => this.onResizeHandleMove(toMove, delta),
            });
        }
        onWillUnmount(() => this.props.onSaveTable(this.props.table));
    }

    onMoveStart() {
        this.startTable = { ...this.props.table };
        // stop the next click event from the touch/click release from unselecting the table
        document.addEventListener("click", (ev) => ev.stopPropagation(), {
            capture: true,
            once: true,
        });
    }

    onMove({ dx, dy }) {
        const { position_h, position_v } = this.startTable;
        const { minX, minY, maxX, maxY } = getLimits(this.root.el, this.props.limit.el);
        this.props.table.position_h = constrain(position_h + dx, minX, maxX);
        this.props.table.position_v = constrain(position_v + dy, minY, maxY);
        this._setElementStyle();
    }

    onResizeHandleMove([moveX, moveY], { dx, dy }) {
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
        this._setElementStyle();
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

    _setElementStyle() {
        const table = this.props.table;
        Object.assign(this.root.el.style, {
            left: `${table.position_h}px`,
            top: `${table.position_v}px`,
            width: `${table.width}px`,
            height: `${table.height}px`,
            background: table.color || "rgb(53, 211, 116)",
            "line-height": `${table.height}px`,
            "border-radius": table.shape === "round" ? "1000px" : "3px",
            "font-size": table.height >= 150 && table.width >= 150 ? "32px" : "16px",
        });
    }
}
