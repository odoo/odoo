import { useLayoutEffect } from "@web/owl2/utils";
import { memoize } from "@web/core/utils/functions";

// ── Batch infrastructure ─────────────────────────────────────────────────────

const pendingResizes = new Map(); // el → options, deduplicates by element
let flushScheduled = false;

function flushResizes() {
    flushScheduled = false;
    const items = [...pendingResizes];
    pendingResizes.clear();

    const inputs = items.filter(([el]) => el instanceof HTMLInputElement);
    const textareas = items.filter(([el]) => !(el instanceof HTMLInputElement));

    // ── Inputs: 3 reflows total regardless of N ──────────────────────────────
    // Phase 1: write 100% to all
    for (const [el] of inputs) {
        el.style.width = "100%";
    }
    // Phase 2: read maxWidths from all
    const maxWidths = inputs.map(([el]) => el.clientWidth);
    // Phase 3: write 10px to all
    for (const [el] of inputs) {
        el.style.width = "10px";
    }
    // Phase 4: read scrollWidths + computed styles from all
    const finalWidths = inputs.map(([el], i) => {
        if (el.value === "" && el.placeholder !== "") {
            return "auto";
        }
        const style = window.getComputedStyle(el);
        let boxExtraWidth = parseFloat(style.borderLeftWidth) + parseFloat(style.borderRightWidth);
        if (doesScrollWidthExcludePadding()) {
            boxExtraWidth += parseFloat(style.paddingLeft) + parseFloat(style.paddingRight);
        }
        const desiredWidth = el.scrollWidth + boxExtraWidth + 1;
        return desiredWidth > maxWidths[i] ? "100%" : `${desiredWidth}px`;
    });
    // Phase 5: write final widths
    for (let i = 0; i < inputs.length; i++) {
        inputs[i][0].style.width = finalWidths[i];
    }

    // ── Textareas: 2 reflows total regardless of N ───────────────────────────
    // Phase 1: read computed styles from all (no reflow)
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
    // Phase 2: write intermediate styles to all (one reflow)
    for (const { el } of textareaData) {
        Object.assign(el.style, {
            height: "auto",
            borderTopWidth: 0,
            borderBottomWidth: 0,
            paddingTop: 0,
            paddingBottom: 0,
        });
    }
    // Phase 3: read scrollHeights from all
    const heights = textareaData.map(({ el, options, heightOffset }) =>
        Math.max(options.minimumHeight || 0, el.scrollHeight + heightOffset)
    );
    // Phase 4: write final styles to all (one reflow)
    for (let i = 0; i < textareaData.length; i++) {
        const { el, previousStyle } = textareaData[i];
        Object.assign(el.style, previousStyle, { height: `${heights[i]}px` });
        el.parentElement.style.height = `${heights[i]}px`;
    }

    // ── Callbacks ─────────────────────────────────────────────────────────────
    for (const [el, options] of items) {
        options.onResize?.(el, options);
    }
}

// ── Public API ───────────────────────────────────────────────────────────────

/**
 * @param {Ref} ref
 */
export function useAutoresize(ref, options = {}) {
    let wasProgrammaticallyResized = false;
    let resize = null;
    useLayoutEffect(
        (el) => {
            if (el) {
                resize = (programmaticResize = false) => {
                    wasProgrammaticallyResized = programmaticResize;
                    if (options.ignoreIfEmpty && !el.value) {
                        return;
                    }
                    pendingResizes.set(el, options);
                    if (!flushScheduled) {
                        flushScheduled = true;
                        queueMicrotask(flushResizes);
                    }
                };
                el.addEventListener("input", () => resize(true));
                const resizeObserver = new ResizeObserver(() => {
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
    useLayoutEffect(() => {
        if (resize) {
            resize(true);
        }
    });
}
// comment

/**
 * Exported for callers that resize a textarea directly (outside useAutoresize).
 * @param {HTMLTextAreaElement} textarea
 * @param {{ minimumHeight?: number }} [options]
 */
export function resizeTextArea(textarea, options = {}) {
    const minimumHeight = options.minimumHeight || 0;
    const style = window.getComputedStyle(textarea);
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
