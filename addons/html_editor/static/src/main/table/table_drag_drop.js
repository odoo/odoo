import { closestElement } from "@html_editor/utils/dom_traversal";
import { Component, useRef, useExternalListener } from "@odoo/owl";
import { BORDER_SENSITIVITY } from "./table_plugin";

export class TableDragDrop extends Component {
    static template = "html_editor.TableDragDrop";
    static props = {
        overlayRect: Object,
        pointerPos: Object,
        type: String,
        close: Function,
        turnIntoRow: Function,
        turnIntoHeader: Function,
        addStep: Function,
        target: { validate: (el) => el.nodeType === Node.ELEMENT_NODE },
        document: { validate: (p) => p.nodeType === Node.DOCUMENT_NODE },
    };

    setup() {
        this.overlayRef = useRef("dragOverlay");
        this.overlayRect = { ...this.props.overlayRect };
        this.pointerPos = { ...this.props.pointerPos };
        this.tableElement = closestElement(this.props.target, "table");
        this.tableBounds = this.tableElement.getBoundingClientRect();
        // Compute bounding rects of rows or column cells
        this.itemRects =
            this.props.type === "row"
                ? [...this.tableElement.rows].map((r) => r.getBoundingClientRect())
                : [...this.props.target.parentElement.cells].map((c) => c.getBoundingClientRect());

        useExternalListener(this.props.document, "pointermove", this.onPointerMove);
        useExternalListener(this.props.document, "pointerup", this.onPointerUp);
        if (this.props.document !== document) {
            // Listen outside the iframe.
            useExternalListener(document, "pointermove", this.onPointerMove);
            useExternalListener(document, "pointerup", this.onPointerUp);
        }
    }

    clearHighlights() {
        // Determine which highlight classes to remove.
        const highlightClasses =
            this.props.type === "row"
                ? ["tr-highlight-top", "tr-highlight-bottom"]
                : ["td-highlight-left", "td-highlight-right"];
        const highlightedElements = this.tableElement.querySelectorAll(
            highlightClasses.map((cls) => `.${cls}`).join(", ")
        );
        // Remove the highlight classes.
        highlightedElements.forEach((el) => el.classList.remove(...highlightClasses));
    }

    getInsertPosition() {
        // Calculate middle of overlay(vertical for row, horizontal for column)
        const overlayMiddle =
            this.props.type === "row"
                ? this.overlayRect.top + this.overlayRect.height / 2
                : this.overlayRect.left + this.overlayRect.width / 2;
        // Index of target row/column where overlay is currently positioned
        const targetIndex = this.itemRects.findIndex((rect) =>
            this.props.type === "row"
                ? rect.top <= overlayMiddle && overlayMiddle <= rect.bottom
                : rect.left <= overlayMiddle && overlayMiddle <= rect.right
        );
        // Calculate the middle of the target row/column
        const targetMiddle =
            this.props.type === "row"
                ? this.itemRects[targetIndex].top + this.itemRects[targetIndex].height / 2
                : this.itemRects[targetIndex].left + this.itemRects[targetIndex].width / 2;

        // Determine whether to insert before or after the target
        // If overlay middle is before target middle, we insert before; otherwise, after
        return { targetIndex, insertBefore: overlayMiddle < targetMiddle };
    }

    onPointerMove(ev) {
        // Calculate min and max positions for overlay to
        // prevent it from going outside the table bounds
        const min =
            this.props.type === "row"
                ? this.tableBounds.top - this.overlayRect.height / 2 + BORDER_SENSITIVITY
                : this.tableBounds.left - this.overlayRect.width / 2 + BORDER_SENSITIVITY;
        const max =
            this.props.type === "row"
                ? this.tableBounds.bottom - this.overlayRect.height / 2 - BORDER_SENSITIVITY
                : this.tableBounds.right - this.overlayRect.width / 2 - BORDER_SENSITIVITY;
        // Update overlay position based on pointer movement, clamped within min/max
        if (this.props.type === "row") {
            this.overlayRect.top = Math.min(
                max,
                Math.max(min, this.overlayRect.top + ev.clientY - this.pointerPos.y)
            );
        } else {
            this.overlayRect.left = Math.min(
                max,
                Math.max(min, this.overlayRect.left + ev.clientX - this.pointerPos.x)
            );
        }
        this.clearHighlights();
        const { targetIndex, insertBefore } = this.getInsertPosition();
        // Highlight the target row or column
        if (this.props.type === "row") {
            const targetRow = this.tableElement.rows[targetIndex];
            targetRow.classList.add(insertBefore ? "tr-highlight-top" : "tr-highlight-bottom");
        } else {
            [...this.tableElement.rows].forEach((row) => {
                const targetCell = row.cells[targetIndex];
                targetCell.classList.add(insertBefore ? "td-highlight-left" : "td-highlight-right");
            });
        }
        // Apply updated overlay position to the overlay element
        const overlayStyle = this.overlayRef.el.style;
        overlayStyle.top = `${this.overlayRect.top}px`;
        overlayStyle.left = `${this.overlayRect.left}px`;
        // Update stored pointer position for next move
        this.pointerPos.x = ev.clientX;
        this.pointerPos.y = ev.clientY;
    }

    onPointerUp() {
        this.clearHighlights();
        const { targetIndex, insertBefore } = this.getInsertPosition();
        // Check if the dragged row/column actually changed position
        const hasPositionChanged = (targetIndex, draggedIndex, insertBefore) =>
            !(
                targetIndex === draggedIndex ||
                (targetIndex === draggedIndex - 1 && !insertBefore) ||
                (targetIndex === draggedIndex + 1 && insertBefore)
            );
        if (this.props.type === "row") {
            const draggedRow = this.props.target.parentElement;
            const draggedIndex = [...this.tableElement.rows].indexOf(draggedRow);
            const targetRow = this.tableElement.rows[targetIndex];
            const hasHeaderRow = this.tableElement.rows[0].firstElementChild.nodeName === "TH";
            let newFirstRow;
            if (draggedIndex === 0) {
                if (!(targetIndex === 0 || (targetIndex === 1 && insertBefore))) {
                    // Make second row the new first if first row is moved
                    newFirstRow = this.tableElement.rows[1];
                }
            } else if (targetIndex === 0 && insertBefore) {
                // New first row if dragged row is dropped before first
                newFirstRow = draggedRow;
            }
            if (newFirstRow) {
                // Copy widths from old first row to new first row
                const firstRowCells = this.tableElement.rows[0].cells;
                const newFirstRowCells = newFirstRow.cells;
                [...firstRowCells].forEach((cell, i) => {
                    if (cell.style.width) {
                        newFirstRowCells[i].style.width = cell.style.width;
                    } else {
                        newFirstRowCells[i].style.width = "";
                    }
                });
                if (hasHeaderRow) {
                    this.props.turnIntoRow(this.tableElement.rows[0]);
                    this.props.turnIntoHeader(newFirstRow);
                }
            }
            // Move the row in the DOM if position actually changed
            if (hasPositionChanged(targetIndex, draggedIndex, insertBefore)) {
                insertBefore ? targetRow.before(draggedRow) : targetRow.after(draggedRow);
                this.props.addStep();
            }
        } else {
            const draggedIndex = [...this.props.target.parentElement.cells].indexOf(
                this.props.target
            );
            const draggedCells = [...this.tableElement.rows].map((row) => row.cells[draggedIndex]);
            // Move the column in the DOM if position actually changed
            if (hasPositionChanged(targetIndex, draggedIndex, insertBefore)) {
                [...this.tableElement.rows].forEach((row, i) => {
                    const targetCell = row.cells[targetIndex];
                    const cellToMove = draggedCells[i];
                    insertBefore ? targetCell.before(cellToMove) : targetCell.after(cellToMove);
                });
                this.props.addStep();
            }
        }
        // Close the overlay after drop
        this.props.close();
    }
}
