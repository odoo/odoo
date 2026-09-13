/** @odoo-module native */
import {
    onMounted,
    onWillDestroy,
    status,
    useComponent,
    useExternalListener,
} from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { makeLogger } from "@web/core/debug/debug_logger";
const log = makeLogger("pos.idle_timer");

const UserPresenceEvents = [
    "mousemove",
    "mousedown",
    "touchmove",
    "click",
    "scroll",
    "keypress",
];

export function useIdleTimer(steps, onAlive) {
    const component = useComponent();
    let lastActivity = browser.performance.now();
    const timers = new Set();
    const state = {
        idle: false,
        get time() {
            return (browser.performance.now() - lastActivity) / 1000;
        },
    };

    const clearTimers = () => {
        for (const timer of timers) {
            browser.clearTimeout(timer);
        }
        timers.clear();
    };

    const resetTimers = () => {
        if (status(component) === "destroyed") {
            log.lifecycle("reset canceled: component destroyed");
            return;
        }
        clearTimers();
        lastActivity = browser.performance.now();
        for (const step of steps) {
            const timer = browser.setTimeout(() => {
                timers.delete(timer);
                if (state.idle) {
                    return;
                }
                state.idle = step.action();
                log.logic("step reached", () => ({
                    timeout: step.timeout,
                    idleFor: state.time,
                    idle: state.idle,
                }));
            }, step.timeout);
            timers.add(timer);
        }
    };

    const onMove = (ev) => {
        if (state.idle) {
            log.logic("activity while idle", () => ({
                event: ev.type,
                idleFor: state.time,
            }));
            state.idle = onAlive(ev);
        }
        resetTimers();
    };

    for (const event of UserPresenceEvents) {
        useExternalListener(window, event, onMove);
    }

    onMounted(resetTimers);
    onWillDestroy(clearTimers);

    return state;
}
