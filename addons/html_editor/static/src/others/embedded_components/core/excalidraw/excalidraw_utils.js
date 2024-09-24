import { useDebounced } from "@web/core/utils/timing";
import { onWillUnmount, useComponent } from "@odoo/owl";

/**
 * This hook can be used to setup temporary mouse events. The returned callback
 * can be passed as a handler for `mousedown` event on a component template.
 * Typical use would be resizing: mousedown on a handle, move the mouse to
 * adapt dimensions, mouseup when finished.
 * @TODO engagement: handle scroll events?
 *
 * @param {Object} options
 * @param {Function} [options.onMouseDown]
 * @param {Function} [options.onMouseMove]
 * @param {Function} [options.onMouseUp]
 * @returns {Function} callback to apply on `mousedown` on a template element
 */
export function useMouseResizeListeners(options) {
    const component = useComponent();
    options.onMouseUp = (options.onMouseUp || (() => {})).bind(component);
    options.onMouseDown = (options.onMouseDown || (() => {})).bind(component);
    const onMouseMove = useDebounced(options.onMouseMove || (() => {}), "animationFrame");
    const onMouseUp = (event) => {
        document.removeEventListener("mousemove", onMouseMove);
        onMouseMove.cancel(true);
        options.onMouseUp(event);
    };
    onWillUnmount(() => {
        document.removeEventListener("mousemove", onMouseMove);
        document.removeEventListener("mouseup", onMouseUp);
    });
    return (event) => {
        options.onMouseDown(event);
        document.addEventListener("mousemove", onMouseMove);
        document.addEventListener("mouseup", onMouseUp, { once: true });
    };
}
