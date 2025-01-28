import { expect } from "@odoo/hoot";
import { manuallyDispatchProgrammaticEvent, scroll } from "@odoo/hoot-dom";
import { endTransition } from "@website/../tests/interactions/snippets/helpers";

export { setupTest } from "@website/../tests/interactions/snippets/helpers";

export const customScroll = async function (scrollingElement, start, end) {
    const step = (end - start) / Math.abs(end - start);
    // Ensure the update of variables with the scroll.
    // Otherwise, we would teleport and not update the
    // values correctly.
    await scroll(scrollingElement, { y: start + step })
    await manuallyDispatchProgrammaticEvent(document, "scroll");
    await scroll(scrollingElement, { y: end });
    await manuallyDispatchProgrammaticEvent(document, "scroll");
    await endTransition();
}

export const checkHeader = function (header, main, core, expectedStatus) {
    const message = `Interaction visibility should be ${expectedStatus.visibility}`;
    expect(core.interactions[0].interaction.isVisible).toBe(expectedStatus.visibility, { message });
    expect(`${main.style.paddingTop ? Math.round(parseFloat(main.style.paddingTop)) : 0}px`).toBe(expectedStatus.paddingTop);
    expect(header).toHaveStyle({ transform: expectedStatus.transform });
    const headerClasses = [...header.classList].sort().join(" ");
    expect(headerClasses).toEqual(expectedStatus.classList);
}

export const getTemplateWithoutHideOnScroll = function (class_name) {
    return `
    <header class="${class_name}" style="height:50px; background-color:#CCFFCC;">
    </header>
    <main style="height:2000px;  background-color:#CCCCFF;">
    </main>
    `
}

export const getTemplateWithHideOnScroll = function (class_name) {
    return `
    <header class="${class_name}" style="background-color:#CCFFCC">
        <div class="o_header_hide_on_scroll" style="height: 20px; background-color:#CCFF33;"></div>
        <div style="height: 30px; background-color:#33FFCC;"></div>
    </header>
    <main style="height:2000px;  background-color:#CCCCFF;">
    </main>
    `
}
