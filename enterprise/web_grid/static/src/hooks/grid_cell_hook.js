/** @odoo-module */

import { useComponent, useEffect } from "@odoo/owl";

export function useMagnifierGlass() {
    const component = useComponent();
    return {
        onMagnifierGlassClick() {
            const { context, domain, title } = component.state.cell;
            component.props.openRecords(title, domain.toList(), context);
        },
    };
}

export function useGridCell() {
    const component = useComponent();
    useEffect(
        /** @param {HTMLElement | null} cellEl */
        (cellEl) => {
            if (!cellEl) {
                component.state.cell = null;
                return;
            }
            component.state.cell = component.props.getCell(
                cellEl.dataset.row,
                cellEl.dataset.column
            );
            Object.assign(component.rootRef.el.style, {
                "grid-row": cellEl.style["grid-row"],
                "grid-column": cellEl.style["grid-column"],
                "z-index": 1,
            });
            component.rootRef.el.dataset.gridRow = cellEl.dataset.gridRow;
            component.rootRef.el.dataset.gridColumn = cellEl.dataset.gridColumn;
            cellEl.querySelector(".o_grid_cell_readonly").classList.add("d-none");
            component.rootRef.el.classList.toggle(
                "o_field_cursor_disabled",
                !component.state.cell.row.isSection && !component.isEditable()
            );
            component.rootRef.el.classList.toggle("fw-bold", Boolean(component.state.cell.row.isSection));
        },
        () => [component.props.reactive.cell]
    );
}
