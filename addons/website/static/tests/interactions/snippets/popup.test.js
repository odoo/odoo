import { expect, test } from "@odoo/hoot";
import {
    click,
    hover,
    isVisible,
    leave,
    manuallyDispatchProgrammaticEvent,
    pointerDown,
    press,
    waitFor,
} from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";
import { startInteractions, setupInteractionWhiteList } from "../../core/helpers";
import { cookie } from "@web/core/browser/cookie";

setupInteractionWhiteList("website.popup");

/**
 * Wait for the modal to show, then for the display animation to end,
 * then do an action, then await the hiding animation to end.
 *
 * @param {HTMLElement} el
 */
async function modalToggleAction(fn) {
    // 1000 is arbitrary to leave enough time.
    await advanceTime(1000);
    await fn();
    // 500 is arbitrary to leave enough time.
    await advanceTime(500);
}

/**
 * @param {Object} options
 * @param {number} options.showAfter - delay
 * @param {string} options.display - one of "afterDelay", "onClick", "mouseExit"
 * @param {boolean} options.backdrop
 * @param {string} options.extraPrimaryBtnClasses
 * @param {string} options.modalId
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
    expect(core.interactions.length).toBe(0);
});

test("close popup with close button and check cookies", async () => {
    const { core, el } = await startInteractions(getPopupTemplate());
    expect(core.interactions.length).toBe(1);
    const modalEl = el.querySelector("#sPopup .modal");
    const closeBtnEl = modalEl.querySelector(".js_close_popup");
    expect(cookie.get("sPopup")).not.toBe("true");
    await waitFor(modalEl, { visible: "true" });
    expect(isVisible(modalEl)).toBe(true);
    await modalToggleAction(async () => await click(closeBtnEl));
    expect(isVisible(modalEl)).toBe(false);
    expect(cookie.get("sPopup")).toBe("true");
});

test("close popup by pressing escape", async () => {
    const { core, el } = await startInteractions(getPopupTemplate());
    expect(core.interactions.length).toBe(1);
    const modalEl = el.querySelector("#sPopup .modal");
    await waitFor(modalEl, { visible: "true" });
    expect(isVisible(modalEl)).toBe(true);
    // Focus the modal so that the escape is dispatched on the right element.
    await pointerDown(modalEl);
    await modalToggleAction(async () => await press("Escape"));
    expect(isVisible(modalEl)).toBe(false);
});

test("click on primary button closes popup", async () => {
    const { core, el } = await startInteractions(getPopupTemplate());
    expect(core.interactions.length).toBe(1);
    const modalEl = el.querySelector("#sPopup .modal");
    const primaryBtnEl = modalEl.querySelector(".btn-primary");
    await waitFor(modalEl, { visible: "true" });
    expect(isVisible(modalEl)).toBe(true);
    await modalToggleAction(async () => await click(primaryBtnEl));
    expect(isVisible(modalEl)).toBe(false);
});

test("click on primary button which is a form submit doesn't close popup", async () => {
    const { core, el } = await startInteractions(getPopupTemplate({ extraPrimaryBtnClasses: "o_website_form_send" }));
    expect(core.interactions.length).toBe(1);
    const modalEl = el.querySelector("#sPopup .modal");
    const primaryBtnEl = modalEl.querySelector(".btn-primary.o_website_form_send");
    await waitFor(modalEl, { visible: "true" });
    expect(isVisible(modalEl)).toBe(true);
    await modalToggleAction(async () => await click(primaryBtnEl));
    expect(isVisible(modalEl)).toBe(true);
});

test("popup shows after 1000ms", async () => {
    const { core, el } = await startInteractions(getPopupTemplate({ showAfter: 1000 }));
    expect(core.interactions.length).toBe(1);
    const modalEl = el.querySelector("#sPopup .modal");
    expect(isVisible(modalEl)).toBe(false);
    // TODO: the next 2 lines don't work, but waitFor with timeout actually
    // waits for 1s. This is not ideal.
    // await advanceTime(1000);
    // await waitFor(modalEl, { visible: "true" });
    await waitFor(modalEl, { visible: "true", timeout: 1000 });
    expect(isVisible(modalEl)).toBe(true);
});

// TODO: do it through clicking on the link rather than dispatching the event.
test("show popup after click on link", async () => {
    const { core, el } = await startInteractions(`
        <a href="#modal">Show popup</a>
        ${getPopupTemplate({ display: "onClick", modalId: "modal" })}
    `);
    expect(core.interactions.length).toBe(1);
    const modalEl = el.querySelector("#sPopup #modal[data-display='onClick']");
    // const linkEl = el.querySelector("a[href='#modal']");
    expect(isVisible(modalEl)).toBe(false);
    // await click(linkEl);
    await manuallyDispatchProgrammaticEvent(window, "hashchange", { newURL: "#modal" });
    await waitFor(modalEl, { visible: "true" });
    expect(isVisible(modalEl)).toBe(true);
});

test("show popup when mouse leaves document", async () => {
    const { core, el } = await startInteractions(getPopupTemplate({ display: "mouseExit" }));
    expect(core.interactions.length).toBe(1);
    const modalEl = el.querySelector("#sPopup .modal");
    expect(isVisible(modalEl)).toBe(false);
    await hover(modalEl.ownerDocument.body);
    await leave(modalEl.ownerDocument.body);
    await waitFor(modalEl, { visible: "true" });
    expect(isVisible(modalEl)).toBe(true);
});

// TODO: fix this test.
// test("cannot scroll while popup open with backdrop", async () => {
//     const { core, el } = await startInteractions(`
//         <span id="span1">Span1</span>
//         <p>Lorem ipsum odor amet, consectetuer adipiscing elit. Sem proin eu orci vestibulum massa pharetra. Conubia magna eget sollicitudin lacus hendrerit ipsum sagittis. Ad mollis non consequat potenti molestie sollicitudin vestibulum? Nulla sociosqu a mauris; quam quisque non non. Efficitur fringilla curabitur at ullamcorper maximus nulla. Eleifend mauris varius primis nulla ridiculus.</p>
//         <p>Amet ligula risus placerat libero; fames netus. Quisque tristique fringilla penatibus, mi vivamus neque feugiat elementum senectus. Pulvinar augue sagittis suspendisse potenti integer amet mollis nibh. Metus mattis fermentum nunc mauris lacus efficitur? Montes cubilia metus taciti viverra mi. Nam velit ligula nec donec blandit himenaeos. Elementum accumsan consectetur sapien molestie; pellentesque laoreet dictum auctor. Himenaeos iaculis ullamcorper efficitur ac ipsum faucibus. Ultrices sollicitudin blandit elit magnis commodo morbi congue.</p>
//         <p>Laoreet gravida nisi feugiat, mollis arcu ut. Pharetra posuere primis interdum id dictumst. Erat quam consequat ut massa sollicitudin aptent primis. Amet quis vehicula dictum consequat nulla dapibus eget laoreet. Ex scelerisque dictumst volutpat nascetur ornare erat pellentesque condimentum nulla. Lacus hendrerit scelerisque arcu pharetra per; massa curabitur blandit ante.</p>
//         <span id="span2">Span2</span>
//         ${getPopupTemplate()}
//     `);
//     const scrollableParent = queryOne("#wrapwrap");
//     scrollableParent.style.height = "150px";
//     scrollableParent.style.overflow = "scroll";
//     // The element must be contained in the scrollable parent (top and bottom)
//     const isVisibleInScroll = (selector) => {
//         const el = queryOne(selector);
//         return (
//             el.getBoundingClientRect().bottom <= scrollableParent.getBoundingClientRect().bottom &&
//             el.getBoundingClientRect().top >= scrollableParent.getBoundingClientRect().top
//         );
//     };

//     expect(core.interactions.length).toBe(1);
//     const modalEl = el.querySelector("#sPopup .modal");
//     await waitFor(modalEl, { visible: "true" });
//     // Starting state: modal visible, span1 visible, span2 not visible
//     expect(isVisible(modalEl)).toBe(true);
//     expect(isVisibleInScroll(queryOne("#span1"))).toBe(true);
//     expect(isVisibleInScroll(queryOne("#span2"))).toBe(false);
//     await hover(scrollableParent);
//     await manuallyDispatchProgrammaticEvent(scrollableParent, "wheel", { deltaY: scrollableParent.scrollHeight });
//     await animationFrame();
//     // While popup open: span1 still visible, span2 still not visible
//     expect(isVisibleInScroll(queryOne("#span1"))).toBe(true);
//     expect(isVisibleInScroll(queryOne("#span2"))).toBe(false);
//     await modalToggleAction(async () => await click(queryOne(".js_close_popup")));
//     expect(isVisible(modalEl)).toBe(false);
//     await hover(scrollableParent);
//     // await manuallyDispatchProgrammaticEvent(scrollableParent, "wheel", { deltaY: scrollableParent.scrollHeight, deltaMode: 1 });
//     await animationFrame();
//     // After closing popup and scrolling: span1 not visible, span2 visible
//     expect(isVisibleInScroll(queryOne("#span1"))).toBe(false);
//     expect(isVisibleInScroll(queryOne("#span2"))).toBe(true);
// });

// Test: can scroll while popup open and no backdrop
