import { useExternalListener, useRef } from "@odoo/owl";

/**
 * @param {string} targetRefName
 * @param {number} [minHeight]
 * @returns {Function} event listener for t-on-mousedown
 */
export function useResizer(targetRefName, minHeight = 100) {
    const targetRef = useRef(targetRefName);
    let isMouseDownOnResizer = false;
    let startOffsetTop, startHeight;
    const onResizerMouseDown = (ev) => {
        isMouseDownOnResizer = true;
        startHeight = targetRef.el.offsetHeight;
        startOffsetTop = ev.pageY;
    };
    useExternalListener(document, "mousemove", (ev) => {
        if (isMouseDownOnResizer) {
            const offsetTop = ev.pageY - startOffsetTop;
            const newHeight = Math.max(startHeight + offsetTop, minHeight);
            targetRef.el.style.height = `${newHeight}px`;
        }
    });
    useExternalListener(document, "mouseup", () => (isMouseDownOnResizer = false));
    return onResizerMouseDown;
}
