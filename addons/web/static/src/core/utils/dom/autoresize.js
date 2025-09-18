// @ts-check

/** @module @web/core/utils/dom/autoresize - useAutoresize hook to auto-grow input/textarea elements on content change */

import { useEffect } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";

/**
 * This is used on text inputs or textareas to automatically resize it based on its
 * content each time it is updated. It takes the reference of the element as
 * parameter and some options. Do note that it may introduce mild performance issues
 * since it will force a reflow of the layout each time the element is updated.
 * Do also note that it only works with textareas that are nested as only child
 * of some parent div (like in the text_field component).
 *
 * @param {{ el: HTMLInputElement | HTMLTextAreaElement | null }} ref
 */
export function useAutoresize(ref, options = {}) {
    let wasProgrammaticallyResized = false;
    let resize = null;
    useEffect(
        (el) => {
            if (el) {
                resize = (programmaticResize = false) => {
                    wasProgrammaticallyResized = programmaticResize;
                    if (options.ignoreIfEmpty && !el.value) {
                        return;
                    }
                    if (el instanceof HTMLInputElement) {
                        resizeInput(el, options);
                    } else {
                        resizeTextArea(
                            /** @type {HTMLTextAreaElement} */ (el),
                            options,
                        );
                    }
                    options.onResize?.(el, options);
                };
                el.addEventListener("input", () => resize(true));
                const resizeObserver = new ResizeObserver(() => {
                    // This ensures that the resize function is not called twice on input or page load
                    if (wasProgrammaticallyResized) {
                        wasProgrammaticallyResized = false;
                        return;
                    }
                    resize();
                });
                resizeObserver.observe(el);
                return () => {
                    el.removeEventListener("input", resize);
                    resizeObserver.unobserve(el);
                    resizeObserver.disconnect();
                    resize = null;
                };
            }
        },
        () => [ref.el],
    );
    useEffect(() => {
        if (resize) {
            resize(true);
        }
    });
}

/**
 * Measure text width using a hidden span element appended to the input's parent.
 * This gives consistent results across element types (input vs span/div) because
 * the measurement span inherits all CSS context (font-variant-numeric, etc.) from
 * the same DOM tree. Input scrollWidth can differ from span text rendering by ~10px
 * in Chromium, causing visual jumping when toggling between readonly and edit mode.
 *
 * @param {HTMLInputElement} input
 * @returns {number} the text width in pixels
 */
function measureTextWidth(input) {
    const span = document.createElement("span");
    span.style.position = "absolute";
    span.style.visibility = "hidden";
    span.style.whiteSpace = "nowrap";
    span.textContent = input.value;
    // Append to parent so the span inherits all CSS context (font, font-variant-numeric,
    // letter-spacing, etc.) from the same DOM tree as the input and its readonly counterpart.
    const container = input.parentNode || document.body;
    container.appendChild(span);
    // Use offsetWidth (not getBoundingClientRect) to match how browser computes
    // integer pixel widths for offsetWidth on the readonly span counterpart.
    const width = span.offsetWidth;
    span.remove();
    return width;
}

/**
 * @param {HTMLInputElement} input
 * @param {{ offset?: number }} [options]
 */
function resizeInput(input, options) {
    // This mesures the maximum width of the input which can get from the flex layout.
    input.style.width = "100%";
    const maxWidth = input.clientWidth;
    // Somehow Safari 16 computes input sizes incorrectly. This is fixed in Safari 17
    const isSafari16 = /Version\/16.+Safari/i.test(browser.navigator.userAgent);
    // Minimum width of the input
    input.style.width = "10px";
    if (input.value === "" && input.placeholder !== "") {
        input.style.width = "auto";
        return;
    }
    // Use span-based measurement for consistent text width across element types.
    // Input scrollWidth can differ from span/block text rendering width by ~10px
    // in Chromium, causing visual jumping when toggling between readonly and edit.
    const textWidth = measureTextWidth(input);
    const width = textWidth + (isSafari16 ? 8 : 0) + (options.offset || 0);
    if (width > maxWidth) {
        input.style.width = "100%";
        return;
    }
    input.style.width = `${width}px`;
}

/**
 * @param {HTMLTextAreaElement} textarea
 * @param {{ minimumHeight?: number }} [options]
 */
export function resizeTextArea(textarea, options = {}) {
    const minimumHeight = options.minimumHeight || 0;
    let heightOffset = 0;
    const style = window.getComputedStyle(textarea);
    if (style.boxSizing === "border-box") {
        const paddingHeight =
            parseFloat(style.paddingTop) + parseFloat(style.paddingBottom);
        const borderHeight =
            parseFloat(style.borderTopWidth) + parseFloat(style.borderBottomWidth);
        heightOffset = borderHeight + paddingHeight;
    }
    const previousStyle = {
        borderTopWidth: style.borderTopWidth,
        borderBottomWidth: style.borderBottomWidth,
        padding: style.padding,
    };
    Object.assign(textarea.style, {
        height: "auto",
        borderTopWidth: 0,
        borderBottomWidth: 0,
        paddingTop: 0,
        paddingBottom: 0,
    });
    textarea.style.height = "auto";
    const height = Math.max(minimumHeight, textarea.scrollHeight + heightOffset);
    Object.assign(textarea.style, previousStyle, { height: `${height}px` });
    textarea.parentElement.style.height = `${height}px`;
}
