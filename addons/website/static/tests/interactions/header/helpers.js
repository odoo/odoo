import { expect } from "@odoo/hoot";
import { scroll } from "@odoo/hoot-dom";

import { endTransition } from "@website/../tests/interactions/snippets/helpers";

export { setupTest } from "@website/../tests/interactions/snippets/helpers";

/**
 * @param {Parameters<scroll>[0]} scrollingElement
 * @param {number} start
 * @param {number} end
 */
export async function customScroll(scrollingElement, start, end) {
    const step = (end - start) / Math.abs(end - start);
    // Ensure the update of variables with the scroll.
    // Otherwise, we would teleport and not update the
    // values correctly.
    await scroll(scrollingElement, { y: start + step });
    await scroll(scrollingElement, { y: end });
    await endTransition();
}

/**
 *
 * @param {import("@odoo/hoot-dom").Target} header
 * @param {HTMLElement} main
 * @param {any} core
 * @param {any} expectedStatus
 */
export function checkHeader(header, main, core, expectedStatus) {
    const message = `Interaction visibility should be ${expectedStatus.visibility}`;
    expect(core.interactions[0].interaction.isVisible).toBe(expectedStatus.visibility, { message });
    expect(`${main.style.paddingTop ? Math.round(parseFloat(main.style.paddingTop)) : 0}px`).toBe(
        expectedStatus.paddingTop
    );
    expect(header).toHaveStyle({ transform: expectedStatus.transform });
    expect(header).toHaveClass(expectedStatus.classList);
}

/**
 * @param {string} className
 */
export function getTemplateWithoutHideOnScroll(className) {
    return /* xml */ `
        <header class="${className}" style="height:50px; background-color:#CCFFCC;">
        </header>
        <main style="height:2000px;  background-color:#CCCCFF;">
        </main>
    `;
}

/**
 * We use a class to set the height of the hide on scroll element because
 * otherwise it would be override by the interaction.
 *
 * @param {string} className
 */
export function getTemplateWithHideOnScroll(className) {
    return /* xml */ `
        <header class="${className}" style="background-color:#CCFFCC">
            <div class="o_header_hide_on_scroll h20" style="background-color:#CCFF33;"></div>
            <div style="height: 30px; background-color:#33FFCC;"></div>
        </header>
        <main style="height:2000px;  background-color:#CCCCFF;">
        </main>
    `;
}
