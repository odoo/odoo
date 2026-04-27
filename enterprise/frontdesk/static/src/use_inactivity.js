/** @odoo-module **/

import { onMounted, onWillUnmount } from "@odoo/owl";

export function useInactivity(callback, delay) {
    let timeoutId = null;
    const resetTimeout = () => {
        if (timeoutId) {
            clearTimeout(timeoutId);
        }
        timeoutId = setTimeout(callback, delay);
    };
    onMounted(() => {
        resetTimeout();
        document.addEventListener("mousemove", resetTimeout);
        document.addEventListener("keydown", resetTimeout);
        document.addEventListener("touchstart", resetTimeout);
    });
    onWillUnmount(() => {
        if (timeoutId) {
            clearTimeout(timeoutId);
        }
        document.removeEventListener("mousemove", resetTimeout);
        document.removeEventListener("keydown", resetTimeout);
        document.removeEventListener("touchstart", resetTimeout);
    });
}
