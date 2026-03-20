import { afterEach, onError } from "@odoo/hoot";

export function preventResizeObserverError() {
    let resizeObserverErrorCount = 0;
    onError((ev) => {
        // commits cb1fcb598f404bd4b0be3a541297cbdc556b29be and f478310d170028b99eb009560382e53330159200
        // This error is sometimes thrown but is essentially harmless as long as it is not thrown
        // indefinitely. cf https://developer.mozilla.org/en-US/docs/Web/API/ResizeObserver#observation_errors
        if (ev.message === "ResizeObserver loop completed with undelivered notifications.") {
            if (resizeObserverErrorCount < 1) {
                ev.preventDefault();
            }
            resizeObserverErrorCount++;
        }
    });

    afterEach(() => {
        resizeObserverErrorCount = 0;
    });
}
