import { useListener } from "@odoo/owl";

/**
 * @param {(() => HTMLElement | null)} targetRef
 *  An Owl 3 signal ref to the element to resize.
 * @param {number} [minHeight]
 * @returns {Function} event listener for t-on-mousedown
 */
export function useResizer(targetRef, minHeight = 100) {
    let isMouseDownOnResizer = false;
    let startOffsetTop, startHeight;
    const onResizerMouseDown = (ev) => {
        isMouseDownOnResizer = true;
        startHeight = targetRef().offsetHeight;
        startOffsetTop = ev.pageY;
    };
    useListener(document, "mousemove", (ev) => {
        if (isMouseDownOnResizer) {
            const offsetTop = ev.pageY - startOffsetTop;
            const newHeight = Math.max(startHeight + offsetTop, minHeight);
            targetRef().style.height = `${newHeight}px`;
        }
    });
    useListener(document, "mouseup", () => (isMouseDownOnResizer = false));
    return onResizerMouseDown;
}
