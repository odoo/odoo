/** @odoo-module alias=@odoo/hoot-mock default=false */

/**
 * @typedef {import("./mock/network").ServerWebSocket} ServerWebSocket
 */

export {
    advanceFrame,
    advanceTime,
    animationFrame,
    cancelAllTimers,
    Deferred,
    delay,
    freezeTime,
    microTick,
    runAllTimers,
    setFrameRate,
    tick,
} from "@odoo/hoot-dom";
export { mockDate, mockTimeZone } from "./mock/date";
export { makeSeededRandom } from "./mock/math";
export { mockPermission, mockSendBeacon, mockUserAgent, mockVibrate } from "./mock/navigator";
export { mockFetch, mockLocation, mockWebSocket, mockWorker } from "./mock/network";
export { flushNotifications } from "./mock/notification";
export { mockTouch, watchKeys, watchListeners } from "./mock/window";
