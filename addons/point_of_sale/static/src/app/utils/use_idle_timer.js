import { useExternalListener, useState } from "@odoo/owl";

const UserPresenceEvents = ["mousemove", "mousedown", "touchmove", "click", "scroll", "keypress"];

export function useIdleTimer(steps, onAlive) {
    const state = useState({
        timeout: new Set(steps.map((s) => s.timeout)),
        idle: false,
        time: 0,
    });

    const checkSteps = () => {
        for (const step of steps) {
            if (step.timeout === state.time * 1000) {
                state.idle = true;
                step.action();
            }
        }
    };

    const onMove = (ev) => {
        if (state.idle) {
            state.idle = false;
            onAlive(ev);
        }
        state.time = 0;
    };

    for (const event of UserPresenceEvents) {
        useExternalListener(window, event, onMove);
    }

    setInterval(() => {
        state.time++;
        if (state.timeout.has(state.time * 1000)) {
            checkSteps();
        }
    }, 1000);

    return state;
}
