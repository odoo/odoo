import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";

import { beforeEach, describe, expect, test } from "@odoo/hoot";
import {
    animationFrame,
    click,
    hover,
    leave,
    manuallyDispatchProgrammaticEvent,
    pointerDown,
    press,
    queryOne,
    tick,
} from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";

import { browser } from "@web/core/browser/browser";
import { cookie } from "@web/core/browser/cookie";
import { defineStyle } from "@web/../tests/web_test_helpers";
import { startInteractionsWithSnippet } from "../helpers";

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

const modal = ".s_popup .modal";

function processPopupHTML({
    beforeHTML = "",
    afterHTML = "",
    showAfter = 0,
    display = "afterDelay",
    backdrop = true,
    extraPrimaryBtnClasses,
    modalId = "",
    focusableElements = false,
    content = "",
    closeButton = true,
} = {}) {
    return (html) => {
        const popupEl = html.querySelector("[data-snippet='s_popup']");
        popupEl.insertAdjacentHTML("beforebegin", beforeHTML);
        popupEl.insertAdjacentHTML("afterend", afterHTML);
        popupEl.id = "sPopup";
        const modalEl = popupEl.querySelector(".modal");
        modalEl.classList.toggle("s_popup_no_backdrop", !backdrop);
        modalEl.id = modalId;
        modalEl.dataset.showAfter = showAfter;
        modalEl.dataset.display = display;
        popupEl.querySelector(".modal-content").innerHTML = `
        ${
            closeButton
                ? '<button class="s_popup_close js_close_popup border-0 p-0 o_we_no_overlay o_not_editable" aria-label="Close">×</button>'
                : ""
        }
        <section>
            ${content}
            <a href="#" class="btn btn-primary ${extraPrimaryBtnClasses}">Primary button</a>
            ${focusableElements ? '<button id="focus">Button 1</button>' : ""}
        </section>`;
    };
}

test("popup interaction does not activate without .s_popup", async () => {
    const { core } = await startInteractions(``);
    expect(core.interactions).toHaveLength(0);
});

describe("close popup", () => {
    beforeEach(removeTransitions);

    test("close popup with close button and check cookies", async () => {
        const { core } = await startInteractionsWithSnippet("s_popup", {
            processHTML: processPopupHTML(),
        });
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
        const { core } = await startInteractionsWithSnippet("s_popup", {
            processHTML: processPopupHTML(),
        });
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
        const { core } = await startInteractionsWithSnippet("s_popup", {
            processHTML: processPopupHTML(),
        });
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
        const { core } = await startInteractionsWithSnippet("s_popup", {
            processHTML: processPopupHTML({ extraPrimaryBtnClasses: "o_website_form_send" }),
        });
        expect(core.interactions).toHaveLength(1);
        await tick();
        await animationFrame();
        expect(modal).toBeVisible();
        await click(".btn-primary.o_website_form_send");
        expect(modal).toBeVisible();
    });

    test("close popup by clicking outside the modal", async () => {
        const { core } = await startInteractionsWithSnippet("s_popup", {
            processHTML: processPopupHTML(),
        });
        expect(core.interactions).toHaveLength(1);
        await tick();
        await animationFrame();
        await advanceTime(100);
        expect(modal).toBeVisible();
        await click(".modal");
        expect(modal).not.toBeVisible();
    });
});

describe("show popup", () => {
    beforeEach(removeTransitions);
    test("popup shows after 5000ms", async () => {
        const { core } = await startInteractionsWithSnippet("s_popup", {
            processHTML: processPopupHTML({ showAfter: 5000 }),
        });
        expect(core.interactions).toHaveLength(1);
        expect(modal).not.toBeVisible();
        await advanceTime(4500);
        expect(modal).not.toBeVisible();
        await advanceTime(1000);
        expect(modal).toBeVisible();
    });

    test("show popup after click on link", async () => {
        const { core } = await startInteractionsWithSnippet("s_popup", {
            processHTML: processPopupHTML({
                display: "onClick",
                modalId: "modal",
                beforeHTML: `<a href="#modal">Show popup</a>`,
            }),
        });
        expect(core.interactions).toHaveLength(1);
        const modal = "#sPopup #modal[data-display='onClick']";
        expect(modal).not.toBeVisible();
        await click("a[href='#modal']");
        await manuallyDispatchProgrammaticEvent(window, "hashchange", {
            newURL: browser.location.hash,
        });
        expect(modal).toBeVisible();
    });

    test.tags("desktop");
    test("show popup when mouse leaves document", async () => {
        const { core } = await startInteractionsWithSnippet("s_popup", {
            processHTML: processPopupHTML({ display: "mouseExit" }),
        });
        expect(core.interactions).toHaveLength(1);
        const modalEl = queryOne("#sPopup .modal");
        expect(modalEl).not.toBeVisible();
        await hover(modalEl.ownerDocument.body);
        await leave();
        expect(modalEl).toBeVisible();
    });
});

describe("trap focus", () => {
    beforeEach(removeTransitions);

    test("focus is trapped when popup opens", async () => {
        const { core } = await startInteractionsWithSnippet("s_popup", {
            processHTML: processPopupHTML({
                modalId: "modal",
                focusableElements: true,
                beforeHTML: `<a href="#">Link</a>`,
            }),
        });
        expect(core.interactions).toHaveLength(1);
        await pointerDown(document.body);
        await tick();
        await animationFrame();
        await advanceTime(100);
        expect("#modal").toBeVisible();
        await tick();
        expect(".btn-primary").toBeFocused();
        await press("Tab");
        expect("#focus").toBeFocused();
        await press("Tab");
        expect(".s_popup_close").toBeFocused();
        await press("Tab");
        expect(".btn-primary").toBeFocused();
        await press("Tab", { shiftKey: true });
        expect(".s_popup_close").toBeFocused();
    });

    test("reset focus on the previous active element when popup is closed", async () => {
        const { core } = await startInteractionsWithSnippet("s_popup", {
            processHTML: processPopupHTML({
                modalId: "modal",
                beforeHTML: `<a id="showLink" href="#">Link</a>`,
            }),
        });
        expect(core.interactions).toHaveLength(1);
        await pointerDown(document.body);
        expect(document.body).toBeFocused(); // Just making sure.
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
        const { core } = await startInteractionsWithSnippet("s_popup", {
            processHTML: processPopupHTML({
                display: "onClick",
                modalId: "modal",
                focusableElements: true,
                beforeHTML: `<a href="#modal">Show popup</a>`,
            }),
        });
        const modal = "#sPopup #modal[data-display='onClick']";
        expect(core.interactions).toHaveLength(1);
        await pointerDown(document.body);
        expect(document.body).toBeFocused(); // Just making sure.
        await press("Tab");
        expect("[href='#modal']").toBeFocused();
        await press("Enter");
        await manuallyDispatchProgrammaticEvent(window, "hashchange", {
            newURL: browser.location.hash,
        });
        expect(modal).toBeVisible();
        await tick();
        await animationFrame();
        await advanceTime(100);
        expect(".btn-primary").toBeFocused();
        await press("Tab");
        expect("#focus").toBeFocused();
        await press("Tab");
        expect(".s_popup_close").toBeFocused();
        await press("Tab");
        expect(".btn-primary").toBeFocused();
        await press("Tab", { shiftKey: true });
        expect(".s_popup_close").toBeFocused();
        await press("Escape");
        expect(modal).not.toBeVisible();
        expect("[href='#modal']").toBeFocused();
    });

    test("intercept & reset focus with no backdrop popup", async () => {
        const { core } = await startInteractionsWithSnippet("s_popup", {
            processHTML: processPopupHTML({
                modalId: "modal",
                backdrop: false,
                beforeHTML: `<a id="link1" href="#">Link</a>`,
            }),
        });
        expect(core.interactions).toHaveLength(1);
        await pointerDown(document.body);
        expect(document.body).toBeFocused(); // Just making sure.
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
        const { core } = await startInteractionsWithSnippet("s_popup", {
            processHTML: processPopupHTML({
                modalId: "modal",
                backdrop: false,
                focusableElements: true,
                beforeHTML: `<a id="link1" href="#">Link before</a>`,
                afterHTML: `<a id="link2" href="#">Link after</a>`,
            }),
        });
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
        expect(".s_popup_close").toBeFocused();
        await press("Tab", { shiftKey: true });
        expect("#link1").toBeFocused();
    });

    test("focus is trapped when popup opens (no close button)", async () => {
        // Tests that the code works in the edge case of missing close button
        const { core } = await startInteractionsWithSnippet("s_popup", {
            processHTML: processPopupHTML({
                beforeHTML: `<a href="#">Link</a>`,
                modalId: "modal",
                closeButton: false,
            }),
        });
        expect(core.interactions).toHaveLength(1);
        await pointerDown(document.body);
        await tick();
        await animationFrame();
        await advanceTime(100);
        expect("#modal").toBeVisible();
        await tick();
        expect(".btn-primary").toBeFocused();
        await press("Tab");
        expect(".btn-primary").toBeFocused();
        await press("Tab", { shiftKey: true });
    });
});

describe("aria-labelledby", () => {
    beforeEach(removeTransitions);

    test("aria-labelledby respects heading priority", async () => {
        const content = "<p>Some text</p><h2>Second heading</h2><h1>Main heading</h1>";
        const { core } = await startInteractionsWithSnippet("s_popup", {
            processHTML: processPopupHTML({
                content,
            }),
        });
        expect(core.interactions).toHaveLength(1);
        await tick();
        const labelID = queryOne("h1").id;
        expect(modal).toHaveAttribute("aria-labelledby", labelID);
        expect(modal).not.toHaveAttribute("aria-label");
    });

    test("aria-labelledby targets first match if multiple choices are available", async () => {
        const content = "<h4 class='target'>First heading</h4><h4>Additional heading</h4>";
        const { core } = await startInteractionsWithSnippet("s_popup", {
            processHTML: processPopupHTML({
                content,
            }),
        });
        expect(core.interactions).toHaveLength(1);
        await tick();
        const labelID = queryOne("h4.target").id;
        expect(modal).toHaveAttribute("aria-labelledby", labelID);
        expect(modal).not.toHaveAttribute("aria-label");
    });

    test("aria-labelledby uses existing ID if present", async () => {
        const content = "<h1 id='heading'>Main heading</h1>";
        const { core } = await startInteractionsWithSnippet("s_popup", {
            processHTML: processPopupHTML({
                content,
            }),
        });
        expect(core.interactions).toHaveLength(1);
        await tick();
        const labelID = queryOne("h1").id;
        expect(labelID).toBe("heading");
        expect(modal).toHaveAttribute("aria-labelledby", "heading");
        expect(modal).not.toHaveAttribute("aria-label");
    });

    test("no aria-labelledby when no suitable element exists and fallback on aria-label", async () => {
        const { core } = await startInteractionsWithSnippet("s_popup", {
            processHTML: processPopupHTML(),
        });
        await tick();
        expect(core.interactions).toHaveLength(1);
        expect(modal).not.toHaveAttribute("aria-labelledby");
        expect(modal).toHaveAttribute("aria-label", "Popup");
    });
});
