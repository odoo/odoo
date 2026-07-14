import { useEffect } from "@odoo/owl";
import { memoize } from "@web/core/utils/functions";

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
                    if (el instanceof HTMLInputElement) {
                        resizeInput(el, options);
                    } else {
                        resizeTextArea(el, options);
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

function resizeInput(input) {
    const style = window.getComputedStyle(input);
    // This mesures the maximum width of the input which can get from the flex layout.
    input.style.width = "100%";
    const maxWidth = input.clientWidth;
    // Minimum width of the input
    input.style.width = "10px";
    if (input.value === "" && input.placeholder !== "") {
        input.style.width = "auto";
        return;
    }
    // scrollWidth measures the content box only; borders are added separately
    let boxExtraWidth = parseFloat(style.borderLeftWidth) + parseFloat(style.borderRightWidth);
    // Some browsers (Safari ≤16, Firefox ≥145) exclude padding from input scrollWidth
    if (doesScrollWidthExcludePadding()) {
        const padding = parseFloat(style.paddingLeft) + parseFloat(style.paddingRight);
        boxExtraWidth += padding;
    }
    const desiredWidth = input.scrollWidth + boxExtraWidth + 1;
    if (desiredWidth > maxWidth) {
        input.style.width = "100%";
        return;
    }
    input.style.width = `${desiredWidth}px`;
}

export function resizeTextArea(textarea, options = {}) {
    const minimumHeight = options.minimumHeight || 0;
    let heightOffset = 0;
    const style = window.getComputedStyle(textarea);
    if (style.boxSizing === "border-box") {
        const paddingHeight = parseFloat(style.paddingTop) + parseFloat(style.paddingBottom);
        const borderHeight = parseFloat(style.borderTopWidth) + parseFloat(style.borderBottomWidth);
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
        paddingRight: style.paddingRight,
        paddingBottom: 0,
        paddingLeft: style.paddingLeft,
    });
    textarea.style.height = "auto";
    const height = Math.max(minimumHeight, textarea.scrollHeight + heightOffset);
    Object.assign(textarea.style, previousStyle, { height: `${height}px` });
    textarea.parentElement.style.height = `${height}px`;
}
