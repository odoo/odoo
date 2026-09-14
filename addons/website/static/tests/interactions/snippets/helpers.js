import { advanceTime, animationFrame, scroll } from "@odoo/hoot-dom";
import { defineStyle } from "@web/../tests/web_test_helpers";
import { makeLogger } from "@web/core/debug/debug_logger";

const log = makeLogger("website.tests.header_geometry");

export async function endTransition() {
    await animationFrame();
    await advanceTime(500);
    log.logic("header after transition", () =>
        JSON.stringify(
            [...document.querySelectorAll("header")].map((el) => ({
                classes: el.className,
                y: el.getBoundingClientRect().y,
                height: el.getBoundingClientRect().height,
                position: getComputedStyle(el).position,
                top: getComputedStyle(el).top,
                transform: getComputedStyle(el).transform,
                parentTransform: getComputedStyle(el.parentElement).transform,
            })),
        ),
    );
}

/**
 * @param {any} core
 * @param {any} wrapwrap
 */
export async function setupTest(core, wrapwrap) {
    wrapwrap.style.height = "800px";
    wrapwrap.style.width = "100%";
    wrapwrap.style.overflow = "scroll";
    core.interactions[0].interaction.scrollingElement = wrapwrap;
    defineStyle(`.hidden { display: none !important; }`);
    defineStyle(`.h20 { height: 20px; }`);
    // The unit bundle does not include website.scss. Fixed-header geometry
    // needs the positioning rule that the public-site bundle supplies.
    defineStyle(
        `.o_header_fixed.o_header_affixed { position: fixed; inset: 0 0 auto 0; }`,
    );
    await endTransition();
}

/**
 * @param {Parameters<scroll>[0]} wrapwrapEl
 * @param {Parameters<scroll>[1]} target
 */
export async function simpleScroll(wrapwrapEl, target) {
    await scroll(wrapwrapEl, target, { scrollable: false });
    await endTransition();
}

/**
 * @param {Parameters<scroll>[0]} wrapwrapEl
 * @param {number} target
 * @param {number} source
 */
export async function doubleScroll(wrapwrapEl, target, source) {
    await scroll(wrapwrapEl, { y: source + (target > source ? 1 : -1) });
    await scroll(wrapwrapEl, { y: target });
    await endTransition();
}
