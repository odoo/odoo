import { animationFrame, advanceTime, scroll } from "@odoo/hoot-dom";

const endTransition = async function () {
    await animationFrame();
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

export const simpleScroll = async function (wrapwrapEl, target) {
    await scroll(wrapwrapEl, target);
    document.dispatchEvent(new Event("scroll"));
    await endTransition();
}

// Scroll twice to correctly updates parameters used by
// onScroll handlers. (cf. Headers)
export const doubleScroll = async function (wrapwrapEl, target, source) {
    await scroll(wrapwrapEl, { y: source + (target > source ? 1 : -1) })
    document.dispatchEvent(new Event("scroll"));
    await scroll(wrapwrapEl, { y: target });
    document.dispatchEvent(new Event("scroll"));
    await endTransition();
}
