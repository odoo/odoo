/** @odoo-module */

import { Draggable } from "@point_of_sale/js/Misc/Draggable";
import { ResizeHandle } from "./resize_handle";
import { onWillUnmount, useEffect, useRef, Component } from "@odoo/owl";
import { Table } from "./table";

const MIN_TABLE_SIZE = 30; // px

function constrain(num, [min, max]) {
    return Math.min(Math.max(num, min), max);
}
export class EditableTable extends Component {
    static template = "pos_restaurant.EditableTable";
    static components = { Draggable, ResizeHandle };
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
        onWillUnmount(() => this.props.onSaveTable(this.props.table));
    }

    onHandleMoveStart() {
        this.startTable = { ...this.props.table };
    }

    onHandleMove(dir, { dx, dy }) {
        const table = this.startTable;
        // Working with min/max x and y makes constraints much easier to apply uniformly
        const { width, height, position_h: minX, position_v: minY } = table;
        const maxX = minX + width;
        const maxY = minY + height;
        const newTable = { minX, minY, maxX, maxY };

        const [moveX, moveY] = this.handles[dir];
        const { limits } = this;
        const bounds = {
            maxX: [minX + MIN_TABLE_SIZE, limits.maxX],
            minX: [limits.minX, maxX - MIN_TABLE_SIZE],
            maxY: [minY + MIN_TABLE_SIZE, limits.maxY],
            minY: [limits.minY, maxY - MIN_TABLE_SIZE],
        };
        newTable[moveX] = constrain(newTable[moveX] + dx, bounds[moveX]);
        newTable[moveY] = constrain(newTable[moveY] + dy, bounds[moveY]);

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

    get limits() {
        const limitRect = this.props.limit.el.getBoundingClientRect();
        const offsetParentRect = this.root.el.offsetParent.getBoundingClientRect();
        return {
            minY: limitRect.top - offsetParentRect.top,
            minX: limitRect.left - offsetParentRect.left,
            maxY: limitRect.top - offsetParentRect.top + limitRect.height,
            maxX: limitRect.left - offsetParentRect.left + limitRect.width,
        };
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

    onDragEnd(event) {
        const { loc } = event.detail;
        const table = this.props.table;
        table.position_v = loc.top;
        table.position_h = loc.left;
    }
}
