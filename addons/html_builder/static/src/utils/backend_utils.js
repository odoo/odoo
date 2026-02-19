import { browser } from "@web/core/browser/browser";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";

/**
 * @param {KeyboardEvent} ev
 * @param {Object} options
 * @param {HTMLElement} [options.containerEl] - closest row containing the columns.
 * Defaults to closest `.row`.
 * @param {HTMLElement} [options.focusedSiblingEl] - focused element, or closest parent
 * whose siblings should be used to navigate. Defaults to `ev.currentTarget`.
 * @param {string} [options.focusElSelector] - if focusedSiblingEl is not the
 * currentTarget, selector to query the focusable child.

 */
export function handleMatrixKeyNavigation(
    ev,
    {
        containerEl = ev.currentTarget.closest(".row"),
        focusedSiblingEl = ev.currentTarget,
        focusElSelector,
    } = {}
) {
    const hotkey = getActiveHotkey(ev);
    if (["arrowup", "arrowdown", "arrowleft", "arrowright", "home", "end"].includes(hotkey)) {
        let nextFocusedEl;
        const reducedMotion = browser.matchMedia("(prefers-reduced-motion: reduce)").matches;
        if (hotkey === "home") {
            nextFocusedEl = containerEl.firstElementChild.firstElementChild;
        } else if (hotkey === "end") {
            nextFocusedEl = containerEl.lastElementChild.lastElementChild;
        } else if (["arrowup", "arrowdown"].includes(hotkey)) {
            ev.preventDefault(); // Do not scroll.
            if (hotkey === "arrowup") {
                if (focusedSiblingEl.matches(":first-child")) {
                    return;
                }
                nextFocusedEl = focusedSiblingEl.previousElementSibling;
            } else if (hotkey === "arrowdown") {
                if (focusedSiblingEl.matches(":last-child")) {
                    return;
                }
                nextFocusedEl = focusedSiblingEl.nextElementSibling;
            }
        } else if (["arrowleft", "arrowright"].includes(hotkey)) {
            const rect = focusedSiblingEl.getBoundingClientRect();
            const columnEl = focusedSiblingEl.parentElement;
            const isLTR =
                (focusedSiblingEl.closest("[dir]").getAttribute("dir") === "ltr") ^
                focusedSiblingEl.closest(".row").matches(".flex-row-reverse");
            let siblingToFocus;
            if (hotkey === "arrowleft") {
                siblingToFocus = isLTR ? "previousElementSibling" : "nextElementSibling";
            } else if (hotkey === "arrowright") {
                siblingToFocus = isLTR ? "nextElementSibling" : "previousElementSibling";
            }
            if (!columnEl[siblingToFocus]) {
                return;
            }
            nextFocusedEl = [...columnEl[siblingToFocus].children].findLast(
                (el) => rect.y + rect.height / 2 >= el.getBoundingClientRect().y
            );
        }
        if (focusElSelector) {
            nextFocusedEl = nextFocusedEl.querySelector(focusElSelector);
        }
        nextFocusedEl.scrollIntoView({
            block: "center",
            behavior: reducedMotion ? "instant" : "smooth",
        });
        nextFocusedEl.focus();
    }
}
