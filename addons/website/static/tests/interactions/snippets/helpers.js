import { animationFrame, advanceTime, manuallyDispatchProgrammaticEvent, scroll } from "@odoo/hoot-dom";
import { defineStyle } from "@web/../tests/web_test_helpers";

export const endTransition = async function () {
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
    defineStyle(/* css */`.hidden { display: none !important; }`);
    defineStyle(/* css */`.h20 { height: 20px; }`);
    await endTransition();
}

export const simpleScroll = async function (wrapwrapEl, target) {
    await scroll(wrapwrapEl, target);
    await manuallyDispatchProgrammaticEvent(document, "scroll");
    await endTransition();
}

// Scroll twice to correctly updates parameters used by onScroll handlers.
// (cf. Headers)
export const doubleScroll = async function (wrapwrapEl, target, source) {
    await scroll(wrapwrapEl, { y: source + (target > source ? 1 : -1) })
    await manuallyDispatchProgrammaticEvent(document, "scroll");
    await scroll(wrapwrapEl, { y: target });
    await manuallyDispatchProgrammaticEvent(document, "scroll");
    await endTransition();
}
