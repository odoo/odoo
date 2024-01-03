/** @odoo-module alias=@odoo/hoot-mock default=false */

/**
 * @typedef {import("./mock/network").ServerWebSocket} ServerWebSocket
 */

export { setRandomSeed } from "./mock/math";
export { mockPermission } from "./mock/navigator";
export { mockFetch, mockWebSocket, mockWorker } from "./mock/network";
export { flushNotifications } from "./mock/notification";
export {
    Deferred,
    advanceTime,
    animationFrame,
    cancelAllTimers,
    delay,
    microTick,
    mockDate,
    mockTimeZone,
    runAllTimers,
    setFrameRate,
    tick,
} from "./mock/time";
