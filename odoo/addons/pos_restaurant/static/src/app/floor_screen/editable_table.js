/** @odoo-module */

import { getLimits, useMovable, constrain } from "@point_of_sale/app/utils/movable_hook";
import { onWillUnmount, useEffect, useRef, Component } from "@odoo/owl";
import { Table } from "@pos_restaurant/app/floor_screen/table";
import { usePos } from "@point_of_sale/app/store/pos_hook";

const MIN_TABLE_SIZE = 30; // px

export class EditableTable extends Component {
    static template = "pos_restaurant.EditableTable";
    static props = {
        onSaveTable: Function,
        limit: { type: Object, shape: { el: [HTMLElement, { value: null }] } },
        table: Table.props.table,
        selectedTables: Array,
    };

    setup() {
        this.pos = usePos();
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
        if (this.pos.floorPlanStyle == "kanban") {
            return;
        }
        this.startTable = { ...this.props.table };
        this.selectedTablesCopy = {};
        for (let i = 0; i < this.props.selectedTables.length; i++) {
            this.selectedTablesCopy[i] = { ...this.props.selectedTables[i] };
        }
        // stop the next click event from the touch/click release from unselecting the table
        document.addEventListener("click", (ev) => ev.stopPropagation(), {
            capture: true,
            once: true,
        });
    }

    onMove({ dx, dy }) {
        if (this.pos.floorPlanStyle == "kanban") {
            return;
        }
        const { minX, minY, maxX, maxY } = getLimits(this.root.el, this.props.limit.el);

        for (const [index, table] of Object.entries(this.selectedTablesCopy)) {
            const position_h = table.position_h;
            const position_v = table.position_v;
            this.props.selectedTables[index].position_h = constrain(position_h + dx, minX, maxX);
            this.props.selectedTables[index].position_v = constrain(position_v + dy, minY, maxY);
        }

        this._setElementStyle();
    }

    onResizeHandleMove([moveX, moveY], { dx, dy }) {
        if (this.pos.floorPlanStyle == "kanban") {
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
        if (this.pos.floorPlanStyle == "kanban") {
            const floor = table.floor;
            const index = floor.tables.indexOf(table);
            const minWidth = 100 + 20;
            const nbrHorizontal = Math.floor(window.innerWidth / minWidth);
            const widthTable = (window.innerWidth - nbrHorizontal * 10) / nbrHorizontal;
            const position_h =
                widthTable * (index % nbrHorizontal) + 5 + (index % nbrHorizontal) * 10;
            const position_v =
                (widthTable + 25) * Math.floor(index / nbrHorizontal) +
                10 +
                Math.floor(index / nbrHorizontal) * 10;

            Object.assign(this.root.el.style, {
                left: `${position_h}px`,
                top: `${position_v}px`,
                width: `${widthTable}px`,
                height: `${widthTable}px`,
                background: table.color || "rgb(53, 211, 116)",
                "line-height": `${widthTable}px`,
                "border-radius": table.shape === "round" ? "1000px" : "3px",
                "font-size": widthTable >= 150 ? "32px" : "16px",
                opacity: "0.7",
            });
            return;
        }
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
