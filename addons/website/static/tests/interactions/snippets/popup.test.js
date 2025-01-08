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
import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";

setupInteractionWhiteList("website.popup");
describe.current.tags("interaction_dev");

/**
 * Remove the CSS transitions because Bootstrap transitions don't work well with
 * Hoot.
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
 * @returns {string} - popup template
 */
function getPopupTemplate(options = {}) {
    const {
        showAfter = 0,
        display = "afterDelay",
        backdrop = true,
        extraPrimaryBtnClasses = "",
        modalId = "",
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
                        </section>
                    </div>
                </div>
            </div>
        </div>
    `;
}

test("popup interaction does not activate without .s_popup", async () => {
    const { core } = await startInteractions(``);
    expect(core.interactions).toHaveLength(0);
});

describe("close popup", () => {
    beforeEach(removeTransitions);
    test("close popup with close button and check cookies", async () => {
        const { core } = await startInteractions(getPopupTemplate());
        expect(core.interactions).toHaveLength(1);
        const modal = "#sPopup .modal";
        expect(cookie.get("sPopup")).not.toBe("true");
        await tick();
        await animationFrame();
        expect(modal).toBeVisible();
        await tick();
        await click(".js_close_popup");
        expect(modal).not.toBeVisible();
        expect(cookie.get("sPopup")).toBe("true");
    });

    test("close popup by pressing escape", async () => {
        const { core } = await startInteractions(getPopupTemplate());
        expect(core.interactions).toHaveLength(1);
        const modal = "#sPopup .modal";
        await tick();
        await animationFrame();
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
        const modal = "#sPopup .modal";
        await tick();
        await animationFrame();
        expect(modal).toBeVisible();
        await tick();
        await click(".btn-primary");
        expect(modal).not.toBeVisible();
    });

    test("click on primary button which is a form submit doesn't close popup", async () => {
        const { core } = await startInteractions(getPopupTemplate({ extraPrimaryBtnClasses: "o_website_form_send" }));
        expect(core.interactions).toHaveLength(1);
        const modal = "#sPopup .modal";
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
        const modal = "#sPopup .modal";
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

    test.tags`desktop`("show popup when mouse leaves document", async () => {
        const { core, el } = await startInteractions(getPopupTemplate({ display: "mouseExit" }));
        expect(core.interactions).toHaveLength(1);
        const modalEl = el.querySelector("#sPopup .modal");
        expect(modalEl).not.toBeVisible();
        await hover(modalEl.ownerDocument.body);
        await leave(modalEl.ownerDocument.body);
        expect(modalEl).toBeVisible();
    });
});
