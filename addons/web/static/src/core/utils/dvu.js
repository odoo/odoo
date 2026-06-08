/**
 * Dynamic Viewport Units (DVU)
 *
 * Provides viewport measurement tools focusing on:
 * - Viewport change tracking for responsive components
 * - Viewport dimensions that respond to virtual keyboard
 *
 * Key differences between visualViewport and standard window dimensions:
 * - On mobile, when virtual keyboards appear, visualViewport.height decreases while
 *   innerHeight often doesn't
 * - During pinch-zoom on mobile, visualViewport dimensions change, while innerWidth/innerHeight
 *   remain static
 * - When mobile browser UI elements (address bars, toolbars) appear/disappear, visualViewport
 *   reflects these changes
 *
 * Enhanced with VirtualKeyboard API support:
 * - Reacts to the keyboard's appearance/disappearance via the geometrychange event
 * - Automatically updates viewport dimensions when keyboard visibility changes
 * - Triggers viewport change listeners when keyboard visibility changes
 *
 * The module will fall back to standard window dimensions when visualViewport API is not
 * available (primarily older browsers or some embedded webviews).
 *
 * References:
 * - https://www.w3.org/blog/CSS/2021/07/15/css-values-4-viewport-units/
 * - https://developer.mozilla.org/en-US/docs/Web/API/VirtualKeyboard_API
 */

import { throttleForAnimation } from "@web/core/utils/timing";
import { onWillUnmount } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { isVirtualKeyboardSupported } from "@web/core/browser/feature_detection";

const viewport = {
    listeners: [],

    /**
     * Register a callback for viewport changes
     *
     * @param {Function} listener - Function to call when viewport changes
     * @returns {Function} - Function to remove the listener
     */
    addListener(listener) {
        this.listeners.push(listener);
        return () => {
            const index = this.listeners.indexOf(listener);
            if (index !== -1) {
                this.listeners.splice(index, 1);
            }
        };
    },

    /**
     * Notify all listeners of viewport changes
     */
    notifyListeners() {
        this.listeners.forEach((listener) => listener());
    },
};

// Initialize viewport tracking
if (typeof window !== "undefined") {
    const throttledUpdate = throttleForAnimation(() => viewport.notifyListeners());

    if (browser.visualViewport) {
        browser.visualViewport.addEventListener("resize", throttledUpdate);
    }

    if (isVirtualKeyboardSupported()) {
        browser.navigator.virtualKeyboard.addEventListener("geometrychange", throttledUpdate);
    }

    // Fallback to window resize for browsers without VisualViewport or VirtualKeyboard
    browser.addEventListener("resize", throttledUpdate);
}

/**
 * Get current viewport dimensions
 * Takes into account VirtualKeyboard API if available
 *
 * @returns {Object} - Object with width and height properties in pixels
 */
export function getViewportDimensions() {
    return {
        width: browser.visualViewport?.width || browser.innerWidth,
        height: browser.visualViewport?.height || browser.innerHeight,
    };
}

/**
 * Register a callback for viewport dimension changes
 * This will trigger for regular viewport changes and virtual keyboard visibility changes
 *
 * @param {Function} callback - Function to call on viewport change
 * @returns {Function} - Function to remove the listener
 */
export function onViewportChange(callback) {
    return viewport.addListener(callback);
}

/**
 * OWL hook to use viewport change tracking in components
 * Automatically cleans up listener when component is unmounted
 *
 * @param {Function} callback - Function to call when viewport changes
 */
export function useViewportChange(callback) {
    const removeListener = onViewportChange(callback);
    onWillUnmount(() => removeListener());
}
