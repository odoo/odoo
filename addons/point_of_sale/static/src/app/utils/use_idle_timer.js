import { useState } from "@odoo/owl";

const UserPresenceEvents = [
    "mousemove",
    "mousedown",
    "touchstart",
    "touchend",
    "touchmove",
    "click",
    "scroll",
    "keypress",
];

export function useIdleTimer(secondes, callback = null) {
    let timeout = null;
    const state = useState({
        idle: false,
    });

    const setIdle = () => {
        clearTimeout(timeout);
        callback && callback();
        state.idle = true;
    };

    const reset = () => {
        clearTimeout(timeout);
        state.idle = false;
        timeout = setTimeout(setIdle, secondes * 1000);
    };

    for (const event of UserPresenceEvents) {
        window.addEventListener(event, reset);
    }

    reset();
    return state;
}
