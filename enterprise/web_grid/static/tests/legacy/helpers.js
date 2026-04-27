/** @odoo-module alias=@web_grid/../tests/helpers default=false */

import { nextTick, triggerEvents } from "@web/../tests/helpers/utils";

/**
 * @param {HTMLElement} cell
 */
export async function hoverGridCell(cell) {
    const rect = cell.getBoundingClientRect();
    const evAttrs = {
        clientX: rect.x,
        clientY: rect.y,
    };
    await triggerEvents(cell, null, ["mouseover", ["mousemove", evAttrs]]);
    await nextTick();
}
