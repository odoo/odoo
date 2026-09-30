import { useEffect } from "@odoo/owl";
import { memoize } from "@web/core/utils/functions";

// Batch resize requests so multiple elements are processed together.
const resizeQueue = new Map(); // el → options, deduplicates by element
let flushScheduled = false;

function flushResizes() {
    flushScheduled = false;
    const items = [...resizeQueue];
    resizeQueue.clear();

    const inputs = items.filter(([el]) => el instanceof HTMLInputElement);
    const textareas = items.filter(([el]) => !(el instanceof HTMLInputElement));

    // Resize inputs in batches to avoid forcing a layout for every element.
    for (const [el] of inputs) {
        el.style.width = "100%";
    }

    const maxWidths = inputs.map(([el]) => el.clientWidth);

    for (const [el] of inputs) {
        el.style.width = "10px";
    }

    const finalWidths = inputs.map(([el], i) => {
        if (el.value === "" && el.placeholder !== "") {
            return "auto";
        }
        const style = window.getComputedStyle(el);
        let extraWidth = parseFloat(style.borderLeftWidth) + parseFloat(style.borderRightWidth);
        if (doesScrollWidthExcludePadding()) {
            extraWidth += parseFloat(style.paddingLeft) + parseFloat(style.paddingRight);
        }
        const desiredWidth = el.scrollWidth + extraWidth + 1;
        return desiredWidth > maxWidths[i] ? "100%" : `${desiredWidth}px`;
    });

    for (let i = 0; i < inputs.length; i++) {
        inputs[i][0].style.width = finalWidths[i];
    }

    // Prepare all textareas before reading their scrollHeight values.
    const textareaData = textareas.map(([el, options]) => {
        const style = window.getComputedStyle(el);
        const previousStyle = {
            borderTopWidth: style.borderTopWidth,
            borderBottomWidth: style.borderBottomWidth,
            padding: style.padding,
        };
        let heightOffset = 0;
        if (style.boxSizing === "border-box") {
            heightOffset =
                parseFloat(style.paddingTop) +
                parseFloat(style.paddingBottom) +
                parseFloat(style.borderTopWidth) +
                parseFloat(style.borderBottomWidth);
        }
        return { el, options, previousStyle, heightOffset };
    });

    // Reset all textareas before measuring their required height.
    for (const { el } of textareaData) {
        Object.assign(el.style, {
            height: "auto",
            borderTopWidth: 0,
            borderBottomWidth: 0,
            paddingTop: 0,
            paddingBottom: 0,
        });
    }

    const heights = textareaData.map(({ el, options, heightOffset }) =>
        Math.max(options.minimumHeight || 0, el.scrollHeight + heightOffset)
    );
    for (let i = 0; i < textareaData.length; i++) {
        const { el, previousStyle } = textareaData[i];
        Object.assign(el.style, previousStyle, { height: `${heights[i]}px` });
        el.parentElement.style.height = `${heights[i]}px`;
    }
    // Run resize callbacks after all dimensions have been updated.
    for (const [element, options] of items) {
        options.onResize?.(element, options);
    }
}

/**
 * This is used on text inputs or textareas to automatically resize it based on its
 * content each time it is updated. It takes the reference of the element as
 * parameter and some options. Do note that it may introduce mild performance issues
 * since it will force a reflow of the layout each time the element is updated.
 * Do also note that it only works with textareas that are nested as only child
 * of some parent div (like in the text_field component).
 *
 * @param {Ref} ref
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
                    resizeQueue.set(el, options);
                    if (!flushScheduled) {
                        flushScheduled = true;
                        queueMicrotask(flushResizes);
                    }
                };
                const onInput = () => resize(true);
                el.addEventListener("input", onInput);
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
                    el.removeEventListener("input", onInput);
                    resizeObserver.unobserve(el);
                    resizeObserver.disconnect();
                    resizeQueue.delete(el);
                    resize = null;
                };
            }
        },
        () => [ref.el]
    );
    useEffect(() => {
        if (resize) {
            resize(true);
        }
    });
}

const doesScrollWidthExcludePadding = memoize(() => {
    const input = document.createElement("input");
    input.style.cssText = `
        position: absolute;
        visibility: hidden;
        padding: 0;
        border: 0;
        width: auto;
    `;
    document.body.appendChild(input);
    const widthWithoutPadding = input.scrollWidth;
    input.style.padding = "10px";
    const widthWithPadding = input.scrollWidth;
    input.remove();
    return widthWithPadding === widthWithoutPadding;
});

/**
 * @param {HTMLTextAreaElement} textarea
 * @param {{ minimumHeight?: number }} [options]
 */
export function resizeTextArea(textarea, options = {}) {
    const minimumHeight = options.minimumHeight || 0;
    let heightOffset = 0;
    const style = window.getComputedStyle(textarea);
    const previousStyle = {
        borderTopWidth: style.borderTopWidth,
        borderBottomWidth: style.borderBottomWidth,
        padding: style.padding,
    };
    if (style.boxSizing === "border-box") {
        heightOffset =
            parseFloat(style.paddingTop) +
            parseFloat(style.paddingBottom) +
            parseFloat(style.borderTopWidth) +
            parseFloat(style.borderBottomWidth);
    }
    Object.assign(textarea.style, {
        height: "auto",
        borderTopWidth: 0,
        borderBottomWidth: 0,
        paddingTop: 0,
        paddingBottom: 0,
    });
    const height = Math.max(minimumHeight, textarea.scrollHeight + heightOffset);
    Object.assign(textarea.style, previousStyle, { height: `${height}px` });
    textarea.parentElement.style.height = `${height}px`;
}
