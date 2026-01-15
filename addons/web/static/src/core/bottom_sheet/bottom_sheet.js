/**
 * BottomSheet
 *
 * @class
 */
import { Component, useState, useRef, onMounted, useExternalListener } from "@odoo/owl";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { useForwardRefToParent } from "@web/core/utils/hooks";
import { useThrottleForAnimation } from "@web/core/utils/timing";
import { compensateScrollbar } from "@web/core/utils/scrolling";
import { getViewportDimensions, useViewportChange } from "@web/core/utils/dvu";
import { clamp } from "@web/core/utils/numbers";
import { browser } from "@web/core/browser/browser";

export class BottomSheet extends Component {
    static template = "web.BottomSheet";

    static defaultProps = {
        class: "",
    };

    static props = {
        // Main props
        component: { type: Function },
        componentProps: { optional: true, type: Object },
        close: { type: Function },

        class: { optional: true },
        role: { optional: true, type: String },

        // Technical props
        ref: { optional: true, type: Function },
        slots: { optional: true, type: Object },
    };

    setup() {
        this.maxHeightPercent = 90;

        this.state = useState({
            isPositionedReady: false, // Sheet is ready for display
            isSnappingEnabled: false,
            isDismissing: false, // Sheet is being dismissed
            progress: 0, // Visual progress (0-1)
        });

        // Measurements and configuration
        this.measurements = {
            viewportHeight: 0,
            naturalHeight: 0,
            maxHeight: 0,
            dismissThreshold: 0,
        };

        // Popover Ref Requirement
        useForwardRefToParent("ref");

        // References
        this.containerRef = useRef("container");
        this.scrollRailRef = useRef("scrollRail");
        this.sheetRef = useRef("sheet");
        this.sheetBodyRef = useRef("ref");

        // Create throttled version for onScroll
        this.throttledOnScroll = useThrottleForAnimation(this.onScroll.bind(this));

        // Adapt dimensions when mobile virtual-keyboards or browsers bars toggle
        useViewportChange(() => {
            if (this.state.isPositionedReady && !this.state.isDismissing) {
                this.updateDimensions();
            }
        });

        // Handle "ESC" key press.
        useHotkey("escape", () => this.slideOut());

        // Handle mobile "back" gesture and "back" navigation button.
        // Push a history state when the BottomSheet opens, intercept the browser's
        // history events, prevents navigation by pushing another state and closes the sheet.
        window.history.pushState({ bottomSheet: true }, "");
        this.handlePopState = () => {
            if (this.state.isPositionedReady && !this.state.isDismissing) {
                window.history.pushState({ bottomSheet: true }, "");
                this.slideOut();
            }
        };
        useExternalListener(window, "popstate", this.handlePopState);

        onMounted(() => {
            const isReduced =
                browser.matchMedia(`(prefers-reduced-motion: reduce)`) === true ||
                browser.matchMedia(`(prefers-reduced-motion: reduce)`).matches === true;

            this.prefersReducedMotion =
                isReduced || getComputedStyle(this.containerRef.el).animationName === "none";

            this.initializeSheet();
            compensateScrollbar(this.scrollRailRef.el, true, true, "padding-right");
        });
    }

    /**
     * Main initialization method for the sheet
     * Sets up measurements, snap points, and event handlers
     */
    initializeSheet() {
        if (!this.containerRef.el || !this.scrollRailRef.el || !this.sheetRef.el) {
            return;
        }

        // Step 1: Take measurements
        this.measureDimensions();

        // Step 2: Apply Dimensions
        this.applyDimensions();

        // Step 3: Set initial position
        this.positionSheet();

        // Step 4: Setup event handlers after everything has been properly resized and positioned
        this.setupEventHandlers();

        // Step 5: Mark as ready
        this.state.isPositionedReady = true;

        if (this.prefersReducedMotion) {
            this.state.isSnappingEnabled = true;
        } else {
            this.sheetRef.el?.addEventListener(
                "animationend",
                () => (this.state.isSnappingEnabled = true),
                {
                    once: true,
                }
            );
            this.sheetRef.el?.addEventListener(
                "animationcancel",
                () => (this.state.isSnappingEnabled = true),
                {
                    once: true,
                }
            );
        }
    }

    /**
     * Updates dimensions when viewport changes
     * Recalculates measurements and snap points while preserving extended state
     */
    updateDimensions() {
        // Temporarily disable snapping during update
        this.state.isSnappingEnabled = false;

        // Update measurements with new viewport dimensions
        this.measureDimensions();
        this.applyDimensions();

        // // Update scroll position
        const scrollTop = this.scrollRailRef.el.scrollTop;

        // Update progress value
        this.updateProgressValue(scrollTop);
    }

    /**
     * Takes measurements of viewport and sheet dimensions
     * Calculates natural height and other key measurements
     */
    measureDimensions() {
        const viewportHeight = getViewportDimensions().height;

        // Calculate heights based on percentages
        const maxHeightPx = (this.maxHeightPercent / 100) * viewportHeight;

        // Reset any previously set constraints to measure natural height
        const sheet = this.sheetRef.el;
        sheet.style.removeProperty("min-height");
        sheet.style.removeProperty("height");

        const naturalHeight = sheet.offsetHeight;
        const initialHeightPx = Math.min(naturalHeight, maxHeightPx);

        // Store all measurements
        this.measurements = {
            viewportHeight,
            naturalHeight,
            initialHeight: initialHeightPx,
            maxHeight: maxHeightPx,
            dismissThreshold: Math.min(initialHeightPx * 0.3, 100),
        };
    }

    /**
     * Applies calculated dimensions to the DOM elements
     * Sets CSS variables and styles based on measurements and snap points
     */
    applyDimensions() {
        const rail = this.scrollRailRef.el;

        // Convert heights to dvh percentages for CSS variables
        const heightPercent = Math.min(
            (this.measurements.initialHeight / this.measurements.viewportHeight) * 100,
            this.maxHeightPercent
        );

        // Set CSS variables for heights
        rail.style.setProperty("--sheet-height", `${heightPercent}dvh`);
        rail.style.setProperty("--sheet-max-height", `${this.measurements.viewportHeight}px`);
        rail.style.setProperty("--dismiss-height", `${this.measurements.initialHeight || 0}px`);
    }

    /**
     * Sets the initial position of the sheet
     * Configures initial scroll position and overflow behavior
     */
    positionSheet() {
        const scrollRail = this.scrollRailRef.el;
        const bodyContent = this.sheetBodyRef.el;

        const scrollValue = this.measurements.maxHeight;

        // Configure body content overflow
        if (bodyContent) {
            bodyContent.style.overflowY = "auto";
        }

        // Set scroll position
        scrollRail.scrollTop = scrollValue || 0;
        scrollRail.style.containerType = "scroll-state size";
    }

    /**
     * Sets up event handlers for scroll and touch events
     */
    setupEventHandlers() {
        const scrollRail = this.scrollRailRef.el;

        // Add scroll event listener
        scrollRail.addEventListener("scroll", this.throttledOnScroll);
    }

    /**
     * Handles scroll events on the rail element
     * Updates progress, handles position snapping, and triggers dismissal
     */
    onScroll() {
        if (!this.scrollRailRef.el) {
            return;
        }

        const scrollTop = this.scrollRailRef.el.scrollTop;

        // Update progress value for visual effects
        this.updateProgressValue(scrollTop);

        // Check for dismissal condition
        if (scrollTop < this.measurements.dismissThreshold) {
            this.slideOut();
        }
    }

    /**
     * Calculates and updates the progress value based on scroll position
     *
     * @param {number} scrollTop - Current scroll position
     */
    updateProgressValue(scrollTop) {
        const initialPosition = this.measurements.naturalHeight;
        const progress = clamp(scrollTop / initialPosition, 0, 1);

        if (Math.abs(this.state.progress - progress) > 0.01) {
            this.state.progress = progress;
        }
    }

    /**
     * Initiates the slide out animation and dismissal
     */
    slideOut() {
        // Prevent duplicate calls
        if (this.state.isDismissing) {
            return;
        }

        if (this.prefersReducedMotion) {
            this.props.close?.();
        } else {
            this.sheetRef.el?.addEventListener("animationend", () => this.props.close?.(), {
                once: true,
            });
            this.sheetRef.el?.addEventListener("animationcancel", () => this.props.close?.(), {
                once: true,
            });
        }

        // Update state to trigger animation
        this.state.isDismissing = true;
        this.state.isSnappingEnabled = false;
    }

    /**
     * Closes the sheet (public API)
     */
    close() {
        this.slideOut();
    }

    /**
     * Handles back button press (public API)
     */
    back() {
        if (this.props.onBack) {
            this.props.onBack();
        } else {
            this.slideOut();
        }
    }
}
