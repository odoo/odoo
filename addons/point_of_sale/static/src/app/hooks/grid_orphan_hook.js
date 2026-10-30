import { onMounted, onPatched, useListener } from "@odoo/owl";

const GRID_ORPHAN_CLASS = "o_pos_grid_orphan";

/**
 * Marks the last child of a grid of several columns with `o_pos_grid_orphan`
 * when it is alone on the last row, so that it can span that row.
 *
 * @param {() => HTMLElement | null} gridRef an Owl 3 signal ref to the grid
 */
export function useGridOrphan(gridRef) {
    function update() {
        const grid = gridRef();
        if (!grid) {
            return;
        }
        // Measure the layout without the class, which moves the child to a row of its own.
        for (const child of grid.querySelectorAll(`:scope > .${GRID_ORPHAN_CLASS}`)) {
            child.classList.remove(GRID_ORPHAN_CLASS);
        }
        const last = grid.lastElementChild;
        if (!last) {
            return;
        }
        const previous = last.previousElementSibling;
        const columns = getComputedStyle(grid).gridTemplateColumns.split(" ").length;
        if (columns > 1 && (!previous || last.offsetTop > previous.offsetTop)) {
            last.classList.add(GRID_ORPHAN_CLASS);
        }
    }
    onMounted(update);
    onPatched(update);
    useListener(window, "resize", update);
}
