import { expect } from "@odoo/hoot";
import { animationFrame, scroll } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";

const endTransition = async function () {
    // Ensure we finish the transition
    await animationFrame();
    // Ensure the class "o_transitioning" is removed
    await advanceTime(500);
}

export const setupTest = async function (core, wrapwrap) {
    wrapwrap.style.height = "800px";
    wrapwrap.style.width = "100%";
    wrapwrap.style.overflow = "scroll";
    core.interactions[0].interaction.scrollingElement = wrapwrap;
    const specialStyle = document.createElement("style");
    specialStyle.innerText = `.hidden {display: none !important;}`
    wrapwrap.closest("html").querySelector("head").appendChild(specialStyle);
    await endTransition();
}

export const customScroll = async function (scrollingElement, start, end) {
    const step = (end - start) / Math.abs(end - start);
    // Ensure the update of variables with the scroll.
    // Otherwise, we would teleport and not update the
    // values correctly.
    await scroll(scrollingElement, { y: start + step })
    document.dispatchEvent(new Event("scroll"));
    await scroll(scrollingElement, { y: end });
    document.dispatchEvent(new Event("scroll"));
    await endTransition();
}

export const checkHeader = function (header, main, core, expectedStatus) {
    const message = `Interaction visibility should be ${expectedStatus.visibility}`;
    expect(core.interactions[0].interaction.isVisible).toBe(expectedStatus.visibility, { message });
    expect(main).toHaveStyle({ paddingTop: expectedStatus.paddingTop });
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
