import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

const INTERVAL_MS = 10000;

/**
 * This service allows to register fallback methods that will be called
 * while the bus is disconnected. It is called immediately upon disconnection
 * then again `interval` milliseconds after the previous call completes.
 */
export const busFallbackService = {
    dependencies: ["bus.monitoring_service"],
    start(env, deps) {
        let intervalId = null;
        const busMonitoring = deps["bus.monitoring_service"];
        const fallbacks = new Set();

        /**
         * When the bus connection is lost, start calling the registered fallback methods.
         * When the bus connection is restored, stop calling the fallback methods.
         * If the user goes offline, stop calling the fallback methods.
         * If the user comes back online and the bus connection is still lost,
         * start calling the fallback methods again.
         */
        busMonitoring.bus.addEventListener("bus:connection_lost", () => {
            startFallbacks();
        });
        window.addEventListener("online", () => {
            if (busMonitoring.isConnectionLost) {
                startFallbacks();
            }
        });

        /**
         * Register a fallback method to be called while the bus is
         * disconnected. It is called immediately upon disconnection.
         *
         * @param {function} fallbackMethod
         */
        function registerFallback(fallbackMethod) {
            if (fallbacks.has(fallbackMethod)) {
                return;
            }

            fallbacks.add(fallbackMethod);
        }

        /**
         * Run one fallback call, then schedule the next one `interval`
         * milliseconds after it completes, so that calls never overlap even
         * when the method takes longer than the interval (e.g. a request
         * timing out because the server is unreachable).
         */
        async function runFallback() {
            if (!busMonitoring.isConnectionLost || !browser.navigator.onLine) {
                stopFallbacks();
                return;
            }

            for (const fallbackMethod of fallbacks) {
                await fallbackMethod();
            }

            intervalId = browser.setTimeout(runFallback, INTERVAL_MS);
        }

        function startFallbacks() {
            if (intervalId === null) {
                console.debug("Bus connection lost, starting fallbacks");
                runFallback();
            }
        }

        function stopFallbacks() {
            console.debug("Bus connection restored, stopping fallbacks");
            browser.clearTimeout(intervalId);
            intervalId = null;
        }

        return {
            registerFallback,
        };
    },
};

registry.category("services").add("bus_fallback_service", busFallbackService);
