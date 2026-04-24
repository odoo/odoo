import { onMounted, onPatched } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { localization } from "@web/core/l10n/localization";

/**
 * Makes a 2D matrix of elements from left to right and from top to bottom.
 *
 * @param {HTMLElement} containerEl
 * @param {string} selector - selector for descendants of containerEl
 * @returns {Array<Array<HTMLElement>>} matrix
 */
function makeElementsPositionMatrix(containerEl, selector) {
    const leftMap = new Map();
    for (const el of containerEl.querySelectorAll(selector)) {
        if (!leftMap.has(el.offsetLeft)) {
            leftMap.set(el.offsetLeft, [el]);
        } else {
            leftMap.get(el.offsetLeft).push(el);
        }
    }
    const matrix = [...leftMap.keys()]
        .sort((a, b) => a - b)
        .map((leftPos) => leftMap.get(leftPos).sort((a, b) => a.offsetTop - b.offsetTop));

    return matrix;
}

/**
 * Handles navigation keys (arrows, home, end, page up, page down) on a 2D
 * layout.
 *
 * @param {KeyboardEvent} ev
 * @param {Object} options
 * @param {Array<Array<HTMLElement>>} options.matrix - 2D navigation matrix
 * @param {HTMLElement} options.activeMatrixEl - currently active matrix sibling
 * @param {string} [options.focusableChildSelector] - selector used if the
 * actual focusable element is a child of `activeMatrixEl`
 */
function handleMatrixKeyNavigation(ev, { matrix, activeMatrixEl, focusableChildSelector }) {
    const hotkey = getActiveHotkey(ev);

    if (
        [
            "arrowup",
            "arrowdown",
            "arrowleft",
            "arrowright",
            "home",
            "end",
            "pagedown",
            "pageup",
        ].includes(hotkey)
    ) {
        ev.preventDefault(); // Do not scroll.
        let nextActiveMatrixEl;
        const elMatrixColIdx = matrix.findIndex((col) => col.includes(activeMatrixEl));
        if (["home", "end"].includes(hotkey)) {
            const isRTL = localization.direction === "rtl";
            const firstCol = isRTL ? matrix.at(-1) : matrix[0];
            const lastCol = isRTL ? matrix[0] : matrix.at(-1);
            nextActiveMatrixEl = hotkey === "home" ? firstCol[0] : lastCol.at(-1);
        } else if (["arrowup", "arrowdown"].includes(hotkey)) {
            const elMatrixColumn = matrix[elMatrixColIdx];
            const elIdx = elMatrixColumn.indexOf(activeMatrixEl);
            if (hotkey === "arrowup") {
                nextActiveMatrixEl = elMatrixColumn[Math.max(elIdx - 1, 0)];
            } else if (hotkey === "arrowdown") {
                nextActiveMatrixEl = elMatrixColumn[Math.min(elIdx + 1, elMatrixColumn.length - 1)];
            }
        } else if (["arrowleft", "arrowright"].includes(hotkey)) {
            const rect = activeMatrixEl.getBoundingClientRect();
            let nextCol;
            if (hotkey === "arrowleft") {
                if (elMatrixColIdx === 0) {
                    return;
                }
                nextCol = matrix[elMatrixColIdx - 1];
            } else if (hotkey === "arrowright") {
                if (elMatrixColIdx === matrix.length - 1) {
                    return;
                }
                nextCol = matrix[elMatrixColIdx + 1];
            }
            nextActiveMatrixEl = nextCol.findLast(
                (el) => rect.y + rect.height / 2 >= el.getBoundingClientRect().y
            );
        } else if (["pageup", "pagedown"].includes(hotkey)) {
            // The default behavior is weird in this context, but implementing
            // a behavior that makes sense (e.g. focus the last visible element
            // and scroll) is complex for little use. Accessibility patterns of
            // similar usecases don't seem to take these keys into account.
            return;
        }
        if (focusableChildSelector) {
            nextActiveMatrixEl = nextActiveMatrixEl.querySelector(focusableChildSelector);
        }
        const reducedMotion = browser.matchMedia("(prefers-reduced-motion: reduce)").matches;
        nextActiveMatrixEl.scrollIntoView({
            block: "nearest",
            behavior: reducedMotion ? "instant" : "smooth",
        });
        nextActiveMatrixEl.focus();
    }
}

/**
 * @param {() => HTMLElement[]} getContainerEls - common container ancestors
 * (one per matrix group)
 * @param {string} matrixSiblingSelector - selector to target the elements
 * to use for the navigation logic (i.e. the elements whose siblings make up the
 * masonry layout). The selector will be queried both up
 * (`ev.currentTarget.closest`) and down (`containerEl.querySelectorAll`).
 * @param {string} [focusableChildSelector] - selector used if the actual
 * actual focusable element is a child of `matrixSiblingSelector`
 * @returns {(ev: KeyboardEvent) => void} keydown event handler
 */
export function useMatrixKeyNavigation(
    getContainerEls,
    matrixSiblingSelector,
    focusableChildSelector
) {
    const matrices = new WeakMap();

    onMounted(() => {
        for (const containerEl of getContainerEls()) {
            if (!containerEl) {
                continue;
            }
            const matrix = makeElementsPositionMatrix(containerEl, matrixSiblingSelector);
            matrices.set(containerEl, matrix);
        }
    });

    onPatched(() => {
        for (const containerEl of getContainerEls()) {
            if (!containerEl) {
                continue;
            }
            if (
                !matrices.has(containerEl) ||
                !matrices.get(containerEl).flat().length !==
                    containerEl.querySelectorAll(matrixSiblingSelector).length ||
                !matrices.get(containerEl)[0][0].isConnected
            ) {
                const matrix = makeElementsPositionMatrix(containerEl, matrixSiblingSelector);
                matrices.set(containerEl, matrix);
            }
        }
    });

    return (ev) => {
        const currentContainerEl = getContainerEls().find((containerEl) =>
            containerEl?.contains(ev.currentTarget)
        );
        if (!currentContainerEl) {
            return;
        }
        const activeMatrixEl = ev.currentTarget.closest(matrixSiblingSelector);
        handleMatrixKeyNavigation(ev, {
            matrix: matrices.get(currentContainerEl),
            activeMatrixEl,
            focusableChildSelector,
        });
    };
}
