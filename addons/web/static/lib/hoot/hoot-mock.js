/** @odoo-module alias=@odoo/hoot-mock default=false */

/**
 * @typedef {import("./mock/network").ServerWebSocket} ServerWebSocket
 */

export { animationFrame } from "@odoo/hoot-dom";
export { makeSeededRandom } from "./mock/math";
export { mockPermission, mockSendBeacon, mockUserAgent, mockVibrate } from "./mock/navigator";
export { mockFetch, mockLocation, mockWebSocket, mockWorker } from "./mock/network";
export { flushNotifications } from "./mock/notification";
export {
    Deferred,
    advanceFrame,
    advanceTime,
    cancelAllTimers,
    delay,
    freezeTime,
    microTick,
    mockDate,
    mockTimeZone,
    runAllTimers,
    setFrameRate,
    tick,
} from "./mock/time";
export { mockTouch, watchKeys, watchListeners } from "./mock/window";
