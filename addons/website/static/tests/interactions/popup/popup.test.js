import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

import { beforeEach, describe, expect, test } from "@odoo/hoot";
import {
    animationFrame,
    click,
    hover,
    leave,
    manuallyDispatchProgrammaticEvent,
    pointerDown,
    press,
    tick,
} from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";

import { browser } from "@web/core/browser/browser";
import { cookie } from "@web/core/browser/cookie";
import { defineStyle } from "@web/../tests/web_test_helpers";

setupInteractionWhiteList("website.popup");

describe.current.tags("interaction_dev");

/**
 * Remove the CSS transitions because Bootstrap transitions don't work with Hoot.
 */
function removeTransitions() {
    defineStyle(/* css */ `
        * {
            transition: none !important;
        }
    `);
}

/**
 * @param {Object} [options]
 * @param {number} [options.showAfter] - delay
 * @param {string} [options.display] - one of "afterDelay", "onClick", "mouseExit"
 * @param {boolean} [options.backdrop]
 * @param {string} [options.extraPrimaryBtnClasses]
 * @param {string} [options.modalId]
 * @param {boolean} [options.focusableElements]
 * @returns {string} - popup template
 */
function getPopupTemplate(options = {}) {
    const {
        showAfter = 0,
        display = "afterDelay",
        backdrop = true,
        extraPrimaryBtnClasses = "",
        modalId = "",
        focusableElements = false,
    } = options;
    return `
        <div class="s_popup o_snippet_invisible" data-vcss="001" data-snippet="s_popup"
             data-name="Popup" id="sPopup" data-invisible="1">
            <div class="modal fade s_popup_middle modal_shown ${backdrop ? "" : "s_popup_no_backdrop"}"
                 id="${modalId}"
                 style="background-color: var(--black-50) !important; display: none;"
                 data-show-after="${showAfter}"
                 data-display="${display}"
                 data-consents-duration="7"
                 data-bs-focus="false"
                 data-bs-backdrop="false"
                 tabindex="-1"
                 aria-label="Popup"
                 aria-modal="true"
                 role="dialog">
                <div class="modal-dialog d-flex">
                    <div class="modal-content oe_structure">
                        <div class="s_popup_close js_close_popup o_we_no_overlay o_not_editable" aria-label="Close">×</div>
                        <section>
                            <a href="#" class="btn btn-primary ${extraPrimaryBtnClasses}">Primary button</a>
                            ${focusableElements ? '<button id="focus">Button 1</button>' : ""}
                        </section>
                    </div>
                </div>
            </div>
        </div>
    `;
}

const modal = "#sPopup .modal";

test("popup interaction does not activate without .s_popup", async () => {
    const { core } = await startInteractions(``);
    expect(core.interactions).toHaveLength(0);
});

describe("close popup", () => {
    beforeEach(removeTransitions);

    test("close popup with close button and check cookies", async () => {
        const { core } = await startInteractions(getPopupTemplate());
        expect(core.interactions).toHaveLength(1);
        expect(cookie.get("sPopup")).not.toBe("true");
        await tick();
        await animationFrame();
        await advanceTime(100);
        expect(modal).toBeVisible();
        await tick();
        await click(".js_close_popup");
        expect(modal).not.toBeVisible();
        expect(cookie.get("sPopup")).toBe("true");
    });

    test("close popup by pressing escape", async () => {
        const { core } = await startInteractions(getPopupTemplate());
        expect(core.interactions).toHaveLength(1);
        await tick();
        await animationFrame();
        await advanceTime(100);
        expect(modal).toBeVisible();
        // Focus the modal so that the escape is dispatched on the right element.
        await pointerDown(modal);
        await tick();
        await press("Escape");
        expect(modal).not.toBeVisible();
    });

    test("click on primary button closes popup", async () => {
        const { core } = await startInteractions(getPopupTemplate());
        expect(core.interactions).toHaveLength(1);
        await tick();
        await animationFrame();
        await advanceTime(100);
        expect(modal).toBeVisible();
        await tick();
        await click(".btn-primary");
        expect(modal).not.toBeVisible();
    });

    test("click on primary button which is a form submit doesn't close popup", async () => {
        const { core } = await startInteractions(getPopupTemplate({ extraPrimaryBtnClasses: "o_website_form_send" }));
        expect(core.interactions).toHaveLength(1);
        await tick();
        await animationFrame();
        expect(modal).toBeVisible();
        await click(".btn-primary.o_website_form_send");
        expect(modal).toBeVisible();
    });
});

describe("show popup", () => {
    beforeEach(removeTransitions);
    test("popup shows after 5000ms", async () => {
        const { core } = await startInteractions(getPopupTemplate({ showAfter: 5000 }));
        expect(core.interactions).toHaveLength(1);
        expect(modal).not.toBeVisible();
        await advanceTime(4500);
        expect(modal).not.toBeVisible();
        await advanceTime(1000);
        expect(modal).toBeVisible();
    });

    test("show popup after click on link", async () => {
        const { core } = await startInteractions(`
            <a href="#modal">Show popup</a>
            ${getPopupTemplate({ display: "onClick", modalId: "modal" })}
        `);
        expect(core.interactions).toHaveLength(1);
        const modal = "#sPopup #modal[data-display='onClick']";
        expect(modal).not.toBeVisible();
        await click("a[href='#modal']");
        await manuallyDispatchProgrammaticEvent(window, "hashchange", { newURL: browser.location.hash });
        expect(modal).toBeVisible();
    });

    test.tags("desktop")("show popup when mouse leaves document", async () => {
        const { core, el } = await startInteractions(getPopupTemplate({ display: "mouseExit" }));
        expect(core.interactions).toHaveLength(1);
        const modalEl = el.querySelector("#sPopup .modal");
        expect(modalEl).not.toBeVisible();
        await hover(modalEl.ownerDocument.body);
        await leave(modalEl.ownerDocument.body);
        expect(modalEl).toBeVisible();
    });
});

describe("trap focus", () => {
    beforeEach(removeTransitions);

    test("focus is trapped when popup opens", async () => {
        const { core, el } = await startInteractions(`
            <a href="#">Link</a>
            ${getPopupTemplate({ modalId: "modal", focusableElements: true })}
        `);
        expect(core.interactions).toHaveLength(1);
        await pointerDown(el.ownerDocument.body);
        await tick();
        await animationFrame();
        await advanceTime(100);
        expect("#modal").toBeVisible();
        await tick();
        expect(".btn-primary").toBeFocused();
        await press("Tab");
        expect("#focus").toBeFocused();
        await press("Tab");
        expect(".btn-primary").toBeFocused();
        await press("Tab", { shiftKey: true });
        expect("#focus").toBeFocused();
    });

    test("reset focus on the previous active element when popup is closed", async () => {
        const { core, el } = await startInteractions(`
            <a id="showLink" href="#">Link</a>
            ${getPopupTemplate({ modalId: "modal" })}
        `);
        expect(core.interactions).toHaveLength(1);
        await pointerDown(el.ownerDocument.body);
        expect(el.ownerDocument.body).toBeFocused(); // Just making sure.
        await press("Tab");
        expect("#showLink").toBeFocused();
        await tick();
        await animationFrame();
        await advanceTime(100);
        expect("#modal").toBeVisible();
        await tick();
        expect(".btn-primary").toBeFocused();
        await click(".s_popup_close");
        expect("#modal").not.toBeVisible();
        expect("#showLink").toBeFocused();
    });

    test("trap & reset focus when popup opens on click", async () => {
        const { core, el } = await startInteractions(`
            <a href="#modal">Show popup</a>
            ${getPopupTemplate({ display: "onClick", modalId: "modal", focusableElements: true })}
        `);
        const modal = "#sPopup #modal[data-display='onClick']";
        expect(core.interactions).toHaveLength(1);
        await pointerDown(el.ownerDocument.body);
        expect(el.ownerDocument.body).toBeFocused(); // Just making sure.
        await press("Tab");
        expect("[href='#modal']").toBeFocused();
        await press("Enter");
        await manuallyDispatchProgrammaticEvent(window, "hashchange", { newURL: browser.location.hash });
        expect(modal).toBeVisible();
        await tick();
        await animationFrame();
        await advanceTime(100);
        expect(".btn-primary").toBeFocused();
        await press("Tab");
        expect("#focus").toBeFocused();
        await press("Tab");
        expect(".btn-primary").toBeFocused();
        await press("Tab", { shiftKey: true });
        expect("#focus").toBeFocused();
        await press("Escape");
        expect(modal).not.toBeVisible();
        expect("[href='#modal']").toBeFocused();
    });

    test("intercept & reset focus with no backdrop popup", async () => {
        const { core, el } = await startInteractions(`
            <a id="link1" href="#">Link</a>
            ${getPopupTemplate({ modalId: "modal", backdrop: false })}
        `);
        expect(core.interactions).toHaveLength(1);
        await pointerDown(el.ownerDocument.body);
        expect(el.ownerDocument.body).toBeFocused(); // Just making sure.
        await press("Tab");
        expect("#link1").toBeFocused();
        await tick();
        await animationFrame();
        await advanceTime(100);
        expect("#modal").toBeVisible();
        await tick();
        expect(".btn-primary").toBeFocused();
        await press("Escape");
        expect("#link1").toBeFocused();
    });

    test("don't trap focus if no backdrop", async () => {
        const { core } = await startInteractions(`
            <a id="link1" href="#">Link before</a>
            ${getPopupTemplate({ modalId: "modal", backdrop: false, focusableElements: true })}
            <a id="link2" href="#">Link after</a>
        `);
        expect(core.interactions).toHaveLength(1);
        await tick();
        await animationFrame();
        await advanceTime(100);
        expect("#modal").toBeVisible();
        await tick();
        expect(".btn-primary").toBeFocused();
        await press("Tab");
        expect("#focus").toBeFocused();
        await press("Tab");
        expect("#link2").toBeFocused();
        await press("Tab", { shiftKey: true });
        expect("#focus").toBeFocused();
        await press("Tab", { shiftKey: true });
        expect(".btn-primary").toBeFocused();
        await press("Tab", { shiftKey: true });
        expect("#link1").toBeFocused();
    });
});
