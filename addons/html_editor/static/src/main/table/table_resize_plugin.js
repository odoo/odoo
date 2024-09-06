import { Plugin } from "@html_editor/plugin";
import {
    closestElement,
    getAdjacentNextSiblings,
    getAdjacentPreviousSiblings,
} from "@html_editor/utils/dom_traversal";
import { getColumnIndex } from "@html_editor/utils/table";
import { BORDER_SENSITIVITY } from "@html_editor/main/table/table_plugin";

export class TableResizePlugin extends Plugin {
    static name = "table_resize";
    static dependencies = ["table"];

    setup() {
        this.addDomListener(this.editable, "mousedown", this.onMousedown);
        this.addDomListener(this.editable, "mousemove", this.onMousemove);
    }

    /**
     * If the mouse is hovering over one of the borders of a table cell element,
     * return the side of that border ('left'|'top'|'right'|'bottom').
     * Otherwise, return false.
     *
     * @private
     * @param {MouseEvent} ev
     * @returns {string|boolean}
     */
    isHoveringTdBorder(ev) {
        const target = /** @type {HTMLElement} */ (ev.target);
        if (ev.target && target.nodeName === "TD" && target.isContentEditable) {
            const targetRect = target.getBoundingClientRect();
            if (ev.clientX <= targetRect.x + BORDER_SENSITIVITY) {
                return "left";
            } else if (ev.clientY <= targetRect.y + BORDER_SENSITIVITY) {
                return "top";
            } else if (ev.clientX >= targetRect.x + target.clientWidth - BORDER_SENSITIVITY) {
                return "right";
            } else if (ev.clientY >= targetRect.y + target.clientHeight - BORDER_SENSITIVITY) {
                return "bottom";
            }
        }
        return false;
    }
    /**
     * Change the cursor to a resizing cursor, in the direction specified. If no
     * direction is specified, return the cursor to its default.
     *
     * @private
     * @param {'col'|'row'|false} direction 'col'/'row' to hint column/row,
     *                                      false to remove the hints
     */
    setTableResizeCursor(direction) {
        const classList = this.editable.classList;
        if (classList.contains("o_col_resize")) {
            classList.remove("o_col_resize");
        }
        if (classList.contains("o_row_resize")) {
            classList.remove("o_row_resize");
        }
        if (direction === "col") {
            this.editable.classList.add("o_col_resize");
        } else if (direction === "row") {
            this.editable.classList.add("o_row_resize");
        }
    }

    /**
     * Resizes a table in the given direction, by "pulling" the border between
     * the given targets (ordered left to right or top to bottom).
     *
     * @param {MouseEvent} ev
     * @param {'col'|'row'} direction
     * @param {HTMLElement} target1
     * @param {HTMLElement} target2
     */
    resizeTable(ev, direction, target1, target2) {
        ev.preventDefault();
        const position = target1 ? (target2 ? "middle" : "last") : "first";
        let [item, neighbor] = [target1 || target2, target2];
        const table = closestElement(item, "table");
        const [sizeProp, positionProp, clientPositionProp] =
            direction === "col" ? ["width", "x", "clientX"] : ["height", "y", "clientY"];

        const isRTL = this.config.direction === "rtl";
        // Preserve current width.
        if (sizeProp === "width") {
            const tableRect = table.getBoundingClientRect();
            table.style[sizeProp] = tableRect[sizeProp] + "px";
        }
        const unsizedItemsSelector = `${
            direction === "col" ? "td" : "tr"
        }:not([style*=${sizeProp}])`;
        for (const unsizedItem of table.querySelectorAll(unsizedItemsSelector)) {
            unsizedItem.style[sizeProp] = unsizedItem.getBoundingClientRect()[sizeProp] + "px";
        }

        // TD widths should only be applied in the first row. Change targets and
        // clean the rest.
        if (direction === "col") {
            let hostCell = closestElement(table, "td");
            const hostCells = [];
            while (hostCell) {
                hostCells.push(hostCell);
                hostCell = closestElement(hostCell.parentElement, "td");
            }
            const nthColumn = getColumnIndex(item);
            const firstRow = [...table.querySelector("tr").children];
            [item, neighbor] = [firstRow[nthColumn], firstRow[nthColumn + 1]];
            for (const td of hostCells) {
                if (
                    td !== item &&
                    td !== neighbor &&
                    closestElement(td, "table") === table &&
                    getColumnIndex(td) !== 0
                ) {
                    td.style.removeProperty(sizeProp);
                }
            }
            if (isRTL && position == "middle") {
                [item, neighbor] = [neighbor, item];
            }
        }

        const MIN_SIZE = 33; // TODO: ideally, find this value programmatically.
        switch (position) {
            case "first": {
                const marginProp =
                    direction === "col" ? (isRTL ? "marginRight" : "marginLeft") : "marginTop";
                const itemRect = item.getBoundingClientRect();
                const tableStyle = getComputedStyle(table);
                const currentMargin = parseFloat(tableStyle[marginProp]);
                let sizeDelta = itemRect[positionProp] - ev[clientPositionProp];
                if (direction === "col" && isRTL) {
                    sizeDelta =
                        ev[clientPositionProp] - itemRect[positionProp] - itemRect[sizeProp];
                }
                const newMargin = currentMargin - sizeDelta;
                const currentSize = itemRect[sizeProp];
                const newSize = currentSize + sizeDelta;
                if (newMargin >= 0 && newSize > MIN_SIZE) {
                    const tableRect = table.getBoundingClientRect();
                    // Check if a nested table would overflow its parent cell.
                    const hostCell = closestElement(table.parentElement, "td");
                    const childTable = item.querySelector("table");
                    const endProp = isRTL ? "left" : "right";
                    if (
                        direction === "col" &&
                        ((hostCell &&
                            tableRect[endProp] + sizeDelta >
                                hostCell.getBoundingClientRect()[endProp] - 5) ||
                            (childTable &&
                                childTable.getBoundingClientRect()[endProp] >
                                    itemRect[endProp] + sizeDelta - 5))
                    ) {
                        break;
                    }
                    table.style[marginProp] = newMargin + "px";
                    item.style[sizeProp] = newSize + "px";
                    if (sizeProp === "width") {
                        table.style[sizeProp] = tableRect[sizeProp] + sizeDelta + "px";
                    }
                }
                break;
            }
            case "middle": {
                const [itemRect, neighborRect] = [
                    item.getBoundingClientRect(),
                    neighbor.getBoundingClientRect(),
                ];
                const [currentSize, newSize] = [
                    itemRect[sizeProp],
                    ev[clientPositionProp] - itemRect[positionProp],
                ];
                const editableStyle = getComputedStyle(this.editable);
                const sizeDelta = newSize - currentSize;
                const currentNeighborSize = neighborRect[sizeProp];
                const newNeighborSize = currentNeighborSize - sizeDelta;
                const maxWidth =
                    this.editable.clientWidth -
                    parseFloat(editableStyle.paddingLeft) -
                    parseFloat(editableStyle.paddingRight);
                const tableRect = table.getBoundingClientRect();
                if (
                    newSize > MIN_SIZE &&
                    // prevent resizing horizontally beyond the bounds of
                    // the editable:
                    (direction === "row" ||
                        newNeighborSize > MIN_SIZE ||
                        tableRect[sizeProp] + sizeDelta < maxWidth)
                ) {
                    // Check if a nested table would overflow its parent cell.
                    const childTable = item.querySelector("table");
                    if (
                        direction === "col" &&
                        childTable &&
                        childTable.getBoundingClientRect().right > itemRect.right + sizeDelta - 5
                    ) {
                        break;
                    }
                    item.style[sizeProp] = newSize + "px";
                    if (direction === "col") {
                        neighbor.style[sizeProp] =
                            (newNeighborSize > MIN_SIZE ? newNeighborSize : currentNeighborSize) +
                            "px";
                    } else if (sizeProp === "width") {
                        table.style[sizeProp] = tableRect[sizeProp] + sizeDelta + "px";
                    }
                }
                break;
            }
            case "last": {
                const itemRect = item.getBoundingClientRect();
                let sizeDelta =
                    ev[clientPositionProp] - (itemRect[positionProp] + itemRect[sizeProp]); // todo: rephrase
                if (direction === "col" && isRTL) {
                    sizeDelta = itemRect[positionProp] - ev[clientPositionProp];
                }
                const currentSize = itemRect[sizeProp];
                const newSize = currentSize + sizeDelta;
                if ((newSize >= 0 || direction === "row") && newSize > MIN_SIZE) {
                    const tableRect = table.getBoundingClientRect();
                    // Check if a nested table would overflow its parent cell.
                    const hostCell = closestElement(table.parentElement, "td");
                    const childTable = item.querySelector("table");
                    const endProp = isRTL ? "left" : "right";
                    if (
                        direction === "col" &&
                        ((hostCell &&
                            tableRect[endProp] + sizeDelta >
                                hostCell.getBoundingClientRect()[endProp] - 5) ||
                            (childTable &&
                                childTable.getBoundingClientRect()[endProp] >
                                    itemRect[endProp] + sizeDelta - 5))
                    ) {
                        break;
                    }
                    if (sizeProp === "width") {
                        table.style[sizeProp] = tableRect[sizeProp] + sizeDelta + "px";
                    }
                    item.style[sizeProp] = newSize + "px";
                }
                break;
            }
        }
    }

    onMousedown(ev) {
        const isHoveringTdBorder = this.isHoveringTdBorder(ev);
        const isRTL = this.config.direction === "rtl";
        if (isHoveringTdBorder) {
            ev.preventDefault();
            const direction =
                { top: "row", right: "col", bottom: "row", left: "col" }[isHoveringTdBorder] ||
                false;
            let target1, target2;
            const column = closestElement(ev.target, "tr");
            if (isHoveringTdBorder === "top" && column) {
                target1 = getAdjacentPreviousSiblings(column).find(
                    (node) => node.nodeName === "TR"
                );
                target2 = closestElement(ev.target, "tr");
            } else if (isHoveringTdBorder === "right") {
                if (isRTL) {
                    target1 = getAdjacentPreviousSiblings(ev.target).find(
                        (node) => node.nodeName === "TD"
                    );
                    target2 = ev.target;
                } else {
                    target1 = ev.target;
                    target2 = getAdjacentNextSiblings(ev.target).find(
                        (node) => node.nodeName === "TD"
                    );
                }
            } else if (isHoveringTdBorder === "bottom" && column) {
                target1 = closestElement(ev.target, "tr");
                target2 = getAdjacentNextSiblings(column).find((node) => node.nodeName === "TR");
            } else if (isHoveringTdBorder === "left") {
                if (isRTL) {
                    target1 = ev.target;
                    target2 = getAdjacentNextSiblings(ev.target).find(
                        (node) => node.nodeName === "TD"
                    );
                } else {
                    target1 = getAdjacentPreviousSiblings(ev.target).find(
                        (node) => node.nodeName === "TD"
                    );
                    target2 = ev.target;
                }
            }
            this.isResizingTable = true;
            this.setTableResizeCursor(direction);
            const resizeTable = (ev) => this.resizeTable(ev, direction, target1, target2);
            const stopResizing = (ev) => {
                ev.preventDefault();
                this.isResizingTable = false;
                this.setTableResizeCursor(false);
                this.dispatch("ADD_STEP");
                this.document.removeEventListener("mousemove", resizeTable);
                this.document.removeEventListener("mouseup", stopResizing);
                this.document.removeEventListener("mouseleave", stopResizing);
            };
            this.document.addEventListener("mousemove", resizeTable);
            this.document.addEventListener("mouseup", stopResizing);
            this.document.addEventListener("mouseleave", stopResizing);
        }
    }
    onMousemove(ev) {
        const direction =
            { top: "row", right: "col", bottom: "row", left: "col" }[this.isHoveringTdBorder(ev)] ||
            false;
        if (direction || !this.isResizingTable) {
            this.setTableResizeCursor(direction);
        }
    }
}
