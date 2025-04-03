/**
 * BottomSheet
 *
 * @class
 */


import { Component, useState, useRef, onMounted, useEffect, useExternalListener } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { useThrottleForAnimation, useDebounced } from "@web/core/utils/timing";
import { compensateScrollbar } from "@web/core/utils/scrolling";
import { getViewportDimensions, useViewportChange } from "@web/core/utils/dvu";
import { clamp } from "@web/core/utils/numbers";

export class BottomSheet extends Component {
    static template = "web.BottomSheet";
    static props = {
        id: { type: Number, optional: true },
        title: { type: String, optional: true },
        showBackBtn: { type: Boolean, optional: true },
        showCloseBtn: { type: Boolean, optional: true },
        withBodyPadding: { type: Boolean, optional: true },
        initialHeightPercent: { type: Number, optional: true },
        maxHeightPercent: { type: Number, optional: true },
        startExpanded: { type: Boolean, optional: true },
        preventDismissOnContentScroll: { type: Boolean, optional: true },
        sheetClasses: { type: String, optional: true },
        onClose: { type: Function, optional: true },
        onBack: { type: Function, optional: true },
        slots: { type: Object, optional: true },
        component: { optional: true },
        componentProps: { type: Object, optional: true },
        isNestedSheet: { type: Boolean, optional: true },
        removeAllSheets: { type: Function, optional: true },
    };

    static defaultProps = {
        title: '',
        showBackBtn: false,
        showCloseBtn: false,
        withBodyPadding: true,
        initialHeightPercent: 50,
        maxHeightPercent: 90,
        startExpanded: false,
        preventDismissOnContentScroll: false,
        sheetClasses: '',
        isNestedSheet: false,
        removeAllSheets: () => {},
    };

    setup() {
        this.state = useState({
            isPositionedReady: false,       // Sheet is ready for display
            isExtended: false,              // Sheet is in extended position
            isDismissing: false,            // Sheet is being dismissed
            isSnappingEnabled: false,       // Scroll Snap behavior enabled
            progress: 0,                    // Visual progress (0-1)
            isInForcedExtendedMode: false   // Forced extended mode at launch
        });

        // Measurements and configuration
        this.measurements = {
            viewportHeight: 0,
            naturalHeight: 0,
            initialHeight: 0,
            extendedHeight: 0,
            dismissThreshold: 0,
            contentRequiresScrolling: false,
        };

        // Snap points for scrolling
        this.snapPoints = {
            dismiss: 0,
            initial: null,
            extended: null
        };

        // Footer's flag
        this.hasFooter = false;

        // References
        this.containerRef = useRef("container");
        this.scrollRailRef = useRef("scrollRail");
        this.sheetRef = useRef("sheet");
        this.sheetBodyRef = useRef("sheetBody");
        this.sheetHandleRef = useRef("sheetHandle");
        this.bottomSheetService = useService("bottomSheet");

        // Create throttled version for onScroll
        this.throttledOnScroll = useThrottleForAnimation(this.onScroll.bind(this));
        this.throttledBodyScroll = useThrottleForAnimation(this.onBodyScroll.bind(this));

        // Create debounced function to enable snapping
        this.enableSnapping = useDebounced(() => {
            this.state.isSnappingEnabled = true;
        }, 50);

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

        // Temporary workaround to make it easy to identify when layout mutations occur
        // Remove when a more robust system will be implemented in the future.
        this.contentObserver = null;

        onMounted(() => {
            this.initializeSheet();
            document.body.classList.add("bottom-sheet-open");
            compensateScrollbar(this.scrollRailRef.el, true, true, "padding-right");

            // Initialize content observer after initial setup
            this.initializeContentObserver();
        });

        useEffect(() => {
            return () => {
                // Clean up observer when component is unmounted
                this.disconnectContentObserver();
            };
        }, () => []);
    }

    /**
     * Main initialization method for the sheet
     * Sets up measurements, snap points, and event handlers
     */
    initializeSheet() {
        if (!this.containerRef.el || !this.scrollRailRef.el || !this.sheetRef.el) return;

        // Step 0: Handle Footer
        this.handleFooter();

        // Step 1: Take measurements
        this.measureDimensions();

        // Step 2: Determine snap points
        this.calculateSnapPoints();

        // Step 3: Apply Dimensions
        this.applyDimensions();

        // Step 4: Set initial position
        this.positionSheet();

        // Step 5: Setup event handlers after everything has been properly resized and positioned
        this.setupEventHandlers();

        // Step 6: Mark as ready
        this.state.isPositionedReady = true;

        // Wait for CSS animation to complete before enabling snap for normal sheets
        const animationDuration = this.getAnimationDuration('--BottomSheet-slideIn-duration');

        // Use setTimeout for the initial animation since it has a specific duration
        setTimeout(() => {
            if (this.sheetHandleRef.el) {
                this.sheetHandleRef.el.focus();
            }
            this.state.isSnappingEnabled = true;
        }, animationDuration);
    }

    /**
     * Updates dimensions when viewport changes
     * Recalculates measurements and snap points while preserving extended state
     */
    handleFooter() {
        const footerEl = this.sheetBodyRef.el.querySelector(".o_bottom_sheet_footer");
        if (!footerEl) return;

        const footerPlaceholder = document.createElement("div");

        // Force a reflow and measure
        footerEl.offsetHeight;
        footerPlaceholder.style.height = footerEl.getBoundingClientRect().height + "px";

        this.sheetBodyRef.el.after(footerPlaceholder);
        this.scrollRailRef.el.appendChild(footerEl);
        this.hasFooter = true;
    }

    /**
     * Updates dimensions when viewport changes
     * Recalculates measurements and snap points while preserving extended state
     */
    updateDimensions() {
        // Store extended state
        const wasExtended = this.state.isExtended;

        // Temporarily disable snapping during update
        this.state.isSnappingEnabled = false;

        // Update measurements with new viewport dimensions
        this.measureDimensions();
        this.calculateSnapPoints();
        this.applyDimensions();

        // Determine new scroll position based on previous state
        let newScrollTop;
        if (wasExtended && this.snapPoints.extended) {
            newScrollTop = this.snapPoints.extended;
        } else if (this.snapPoints.initial) {
            newScrollTop = this.snapPoints.initial;
        } else {
            newScrollTop = 0;
        }

        // Update scroll position
        this.scrollRailRef.el.scrollTop = newScrollTop;

        // Re-enable snapping after a short delay
        // Cancel any existing call first
        this.enableSnapping.cancel();
        this.enableSnapping();

        // Update progress value
        this.updateProgressValue(newScrollTop);
    }

    /**
     * Takes measurements of viewport and sheet dimensions
     * Calculates natural height and other key measurements
     */
    measureDimensions() {
        const viewportHeight = getViewportDimensions().height;

        // Calculate heights based on percentages
        const initialHeightPx = (this.props.initialHeightPercent / 100) * viewportHeight;
        const maxHeightPx = (this.props.maxHeightPercent / 100) * viewportHeight;

        // Reset any previously set constraints to measure natural height
        const sheet = this.sheetRef.el;
        sheet.style.removeProperty('min-height');
        sheet.style.removeProperty('height');
        sheet.style.maxHeight = 'none';

        // Force a reflow and measure
        sheet.offsetHeight;
        const naturalHeight = sheet.offsetHeight;

        // Store all measurements
        this.measurements = {
            viewportHeight,
            naturalHeight,
            initialHeight: initialHeightPx,
            extendedHeight: maxHeightPx,
            dismissThreshold: Math.min(initialHeightPx * 0.3, 100),
            contentRequiresScrolling: naturalHeight > maxHeightPx
        };
    }

    /**
     * Determines appropriate snap points based on content and viewport size
     * Sets dismiss, initial, and extended snap points
     */
    calculateSnapPoints() {
        const { naturalHeight, initialHeight, extendedHeight } = this.measurements;

        // Default dismiss point is always 0
        this.snapPoints.dismiss = 0;

        // Determine if we need one or two snap points based on content size
        if (naturalHeight <= initialHeight) {
            // Small content: only one snap point at natural height
            this.snapPoints.initial = naturalHeight;
            this.snapPoints.extended = null;
        } else if (naturalHeight <= extendedHeight) {
            // Medium content: initial at configured height, extended at natural height
            this.snapPoints.initial = initialHeight;
            this.snapPoints.extended = naturalHeight;
        } else {
            // Large content: both snap points at configured heights
            this.snapPoints.initial = initialHeight;
            this.snapPoints.extended = extendedHeight;
        }
    }

    /**
     * Applies calculated dimensions to the DOM elements
     * Sets CSS variables and styles based on measurements and snap points
     */
    applyDimensions() {
        const container = this.containerRef.el;
        const rail = this.scrollRailRef.el;
        const sheet = this.sheetRef.el;
        const viewportHeight = this.measurements.viewportHeight;

        // Convert heights to dvh percentages for CSS variables
        const initialHeightPercent = this.snapPoints.initial ?
            (this.snapPoints.initial / viewportHeight * 100) : this.props.initialHeightPercent;

        const maxHeightPercent = this.snapPoints.extended ?
            (this.snapPoints.extended / viewportHeight * 100) : this.props.maxHeightPercent;

        // Set CSS variables for heights
        rail.style.setProperty('--sheet-initial-height', `${initialHeightPercent}dvh`);
        rail.style.setProperty('--sheet-max-height', `${maxHeightPercent}dvh`);
        rail.style.setProperty('--dismiss-height', `${this.snapPoints.initial || 0}px`);

        // Reset max-height to appropriate value
        sheet.style.maxHeight = `${maxHeightPercent}dvh`;

        if (this.hasFooter) {
            container.classList.toggle("o_bottom_sheet_footer_shadow", this.measurements.contentRequiresScrolling || this.snapPoints.extended);
            container.classList.add('o_bottom_sheet_has_footer');
        }
    }

    /**
     * Sets the initial position of the sheet
     * Configures initial scroll position and overflow behavior
     */
    positionSheet() {
        const scrollRail = this.scrollRailRef.el;
        const bodyContent = this.sheetBodyRef.el;

        let scrollValue;

        if (this.props.startExpanded && this.snapPoints.extended) {
            // Start at extended position
            this.state.isExtended = true;
            this.state.isInForcedExtendedMode = true;
            scrollValue = this.snapPoints.extended;

            // Enable content scrolling immediately
            if (bodyContent) {
                bodyContent.style.overflowY = 'auto';
            }
        } else {
            // Use initial position if available, otherwise extended
            const hasInitialSnap = this.snapPoints.initial !== null;
            this.state.isExtended = !hasInitialSnap && this.snapPoints.extended !== null;
            this.state.isInForcedExtendedMode = false;
            scrollValue = hasInitialSnap ? this.snapPoints.initial : this.snapPoints.extended;

            // Configure body content overflow
            if (bodyContent) {
                bodyContent.style.overflowY = this.measurements.contentRequiresScrolling ? 'hidden' : 'auto';
            }
        }

        // Set scroll position
        scrollRail.scrollTop = scrollValue || 0;
    }

    /**
     * Sets up event handlers for scroll and touch events
     */
    setupEventHandlers() {
        const scrollRail = this.scrollRailRef.el;
        const bodyContent = this.sheetBodyRef.el;

        // Add scroll event listener
        scrollRail.addEventListener('scroll', this.throttledOnScroll);

        if (this.hasFooter && this.measurements.contentRequiresScrolling) {
            bodyContent.addEventListener('scroll', this.throttledBodyScroll);
        }
    }

    /**
     * Handles scroll events on the rail element
     * Updates progress, handles position snapping, and triggers dismissal
     */
    onScroll() {
        if (!this.scrollRailRef.el) return;

        const scrollTop = this.scrollRailRef.el.scrollTop;
        const { dismiss, initial, extended } = this.snapPoints;
        const threshold = 20; // Snap threshold

        // Update progress value for visual effects
        this.updateProgressValue(scrollTop);

        // Check for dismissal condition
        if (Math.abs(scrollTop - dismiss) <= threshold && scrollTop < this.measurements.dismissThreshold) {
            this.slideOut();
            return;
        }

        // Track previous state
        const wasExtended = this.state.isExtended;

        // At extended position
        if (extended && Math.abs(scrollTop - extended) <= threshold) {
            if (!this.state.isExtended) {
                this.state.isExtended = true;
                // Enable content scrolling
                if (this.sheetBodyRef.el) {
                    this.sheetBodyRef.el.style.overflow = 'auto';
                }

                if (this.hasFooter && !this.measurements.contentRequiresScrolling) {
                    this.containerRef.el.classList.remove("o_bottom_sheet_footer_shadow");
                }
            }
        }
        // At initial position
        else if (initial && Math.abs(scrollTop - initial) <= threshold) {
            if (this.state.isExtended) {
                this.state.isExtended = false;

                // Reset scroll position
                if (this.sheetBodyRef.el) {
                    this.sheetBodyRef.el.scrollTop = 0;
                }

                // Reset forced extended mode flag
                if (this.state.isInForcedExtendedMode) {
                    this.state.isInForcedExtendedMode = false;
                }

                if (this.hasFooter && extended) {
                    this.containerRef.el.classList.add("o_bottom_sheet_footer_shadow");
                }
            }
        }

        // Update content scrolling if position changed
        if (wasExtended !== this.state.isExtended) {
            this.updateContentScrolling(this.state.isExtended);
        }
    }

     /**
     * Handles scroll events on the body element
     */
    onBodyScroll() {
        if (!this.sheetBodyRef.el ) return;

        const sheetBody = this.sheetBodyRef.el;
        const showShadow = (sheetBody.scrollHeight - sheetBody.scrollTop) - sheetBody.clientHeight;
        this.containerRef.el.classList.toggle("o_bottom_sheet_footer_shadow", showShadow);
    }

    /**
     * Calculates and updates the progress value based on scroll position
     * Progress will be 1 when sheet reaches initial position, and remains 1 when extended
     *
     * @param {number} scrollTop - Current scroll position
    */
    updateProgressValue(scrollTop) {
        const initialPosition = this.snapPoints.initial || 1;
        const progress = clamp(scrollTop / initialPosition, 0, 1);

        if (Math.abs(this.state.progress - progress) > 0.01) {
            this.state.progress = progress;
        }
    }

    /**
     * Updates content scrolling behavior based on sheet position
     *
     * @param {boolean} isExtended - Whether the sheet is in extended position
     */
    updateContentScrolling(isExtended) {
        if (!this.sheetBodyRef.el) return;

        const bodyContent = this.sheetBodyRef.el;

        if (isExtended) {
            // At extended position, always enable scrolling
            bodyContent.style.overflowY = 'auto';
        } else {
            // At initial, reset scroll position
            bodyContent.scrollTop = 0;

            // Set overflow based on content size
            bodyContent.style.overflowY = this.measurements.contentRequiresScrolling ? 'hidden' : 'auto';
        }
    }

    /**
     * Snaps the sheet to a specific position
     *
     * @param {string} position - Target position ('dismiss', 'initial', or 'extended')
     */
    snapToPosition(position) {
        if (!this.scrollRailRef.el) return;

        const scrollRail = this.scrollRailRef.el;
        let targetPosition = this.snapPoints[position];

        // If target position doesn't exist, try alternative
        if (targetPosition === null) {
            if (position === 'initial' && this.snapPoints.extended) {
                targetPosition = this.snapPoints.extended;
            } else if (position === 'extended' && this.snapPoints.initial) {
                targetPosition = this.snapPoints.initial;
            } else {
                return; // No valid position
            }
        }

        // Smooth scroll to target
        scrollRail.scrollTo({
            top: targetPosition,
            behavior: 'smooth'
        });
    }

    /**
     * Initiates the slide out animation and dismissal
     */
    slideOut() {
        // Prevent duplicate calls
        if (this.state.isDismissing) return;

        // Update state to trigger animation
        this.state.isDismissing = true;
        this.state.isSnappingEnabled = false;

        // Cancel any pending snapping operations
        this.enableSnapping.cancel();

        // Get animation duration for the current sheet
        const animationDuration = this.getAnimationDuration('--BottomSheet-slideOut-duration');

        // Wait for animation to complete
        setTimeout(() => {
            if (this.props.id !== undefined) {
                this.bottomSheetService.remove(this.props.id);
            }

            if (this.props.onClose) {
                this.props.onClose();
            }

            // If there are other sheets in the stack, remove them
            if (this.props.removeAllSheets) {
                // Only remove other sheets, no need to remove the current one
                this.props.removeAllSheets(false);
            }
        }, animationDuration);
    }

    /**
     * Gets animation duration from CSS variable
     *
     * @param {string} property - CSS variable name
     * @returns {number} - Duration in milliseconds
     */
    getAnimationDuration(property) {
        if (!this.containerRef.el) return 450;

        const durationStr = getComputedStyle(this.containerRef.el).getPropertyValue(property).trim();

        if (!durationStr) return 450;

        if (durationStr.endsWith('ms')) {
            return parseFloat(durationStr) + 50;
        } else if (durationStr.endsWith('s')) {
            return (parseFloat(durationStr) * 1000) + 50;
        }

        return parseFloat(durationStr) || 450;
    }

    /**
     * Expands the sheet to extended position (public API)
     */
    expandSheet() {
        if (this.snapPoints.extended) {
            this.snapToPosition('extended');
        }
    }

    /**
     * Collapses the sheet to initial position (public API)
     */
    collapseSheet() {
        if (this.snapPoints.initial) {
            this.snapToPosition('initial');
        } else {
            this.slideOut();
        }
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

    /**
    * Initializes a MutationObserver to monitor height changes in sheet body
    * TEMPORARY SOLUTION: This observer will be replaced with a more robust system in the future
    */
    initializeContentObserver() {
        if (!this.sheetBodyRef.el) return;

        // Disconnect any existing observer to prevent duplicates
        this.disconnectContentObserver();

        // Create new MutationObserver
        this.contentObserver = new MutationObserver(this.handleContentMutation.bind(this));

        // Configure observer to watch for:
        // 1. Direct changes to element attributes (like style.height)
        // 2. Changes to child elements (additions, removals)
        // 3. Changes to text content that might affect layout
        this.contentObserver.observe(this.sheetBodyRef.el, {
            attributes: true,
            childList: true,
            subtree: true,
            characterData: true
        });
    }

    /**
    * Handles mutations detected in the sheet body content
    * Recomputes dimensions and restores appropriate position
    *
    * TEMPORARY SOLUTION: This handler will be replaced with a more robust system in the future
    *
    * @param {MutationRecord[]} mutations - List of mutation records
    */
    handleContentMutation(mutations) {
        // Skip if sheet is not ready or being dismissed
        if (!this.state.isPositionedReady || this.state.isDismissing) return;

        // Skip if no scroll rail reference (needed for position)
        if (!this.scrollRailRef.el) return;

        // Check if any relevant mutations occurred that might affect height
        const hasRelevantMutations = mutations.some(mutation => {
            // Check for style attribute changes
            if (mutation.type === 'attributes' && mutation.attributeName === 'style') {
                return true;
            }

            // Check for added/removed nodes
            if (mutation.type === 'childList' &&
                (mutation.addedNodes.length > 0 || mutation.removedNodes.length > 0)) {
                return true;
            }

            // Text content changes in subtree might affect layout
            if (mutation.type === 'characterData') {
                return true;
            }

            return false;
        });

        // Exit early if no relevant mutations found
        if (!hasRelevantMutations) return;

        // Store current positions and state
        const currentScrollTop = this.scrollRailRef.el.scrollTop;
        const wasExtended = this.state.isExtended;
        const initialPosition = this.snapPoints.initial;

        // Temporarily disable snapping during update
        const wasSnappingEnabled = this.state.isSnappingEnabled;
        this.state.isSnappingEnabled = false;

        // Cancel any pending snapping operations
        this.enableSnapping.cancel();

        // Update dimensions after a small delay to ensure DOM is settled
        setTimeout(() => {
            // Recalculate measurements and snap points
            this.measureDimensions();
            this.calculateSnapPoints();
            this.applyDimensions();

            // Determine target position based on previous state
            let targetScrollTop;

            if (currentScrollTop <= (initialPosition / 2)) {
                // Sheet was near dismiss position - keep it there
                targetScrollTop = currentScrollTop;
            } else if (wasExtended && this.snapPoints.extended) {
                // Sheet was extended - restore to extended position
                targetScrollTop = this.snapPoints.extended;
            } else if (this.snapPoints.initial && currentScrollTop >= (initialPosition / 2)) {
                // Sheet was at or near initial position - restore to initial
                targetScrollTop = this.snapPoints.initial;
            } else {
                // Default to current position
                targetScrollTop = currentScrollTop;
            }

            // Update scroll position
            this.scrollRailRef.el.scrollTop = targetScrollTop;

            // Update progress value
            this.updateProgressValue(targetScrollTop);

            // Restore snapping state after a delay
            setTimeout(() => {
                this.state.isSnappingEnabled = wasSnappingEnabled;

                // Re-enable snapping after a short delay if it was enabled
                if (wasSnappingEnabled) {
                    this.enableSnapping();
                }
            }, 50);
        }, 50);
    }

    /**
    * Disconnects the content observer if it exists
    *
    * TEMPORARY SOLUTION: This cleanup will be removed with the observer in the future
    */
    disconnectContentObserver() {
        if (this.contentObserver) {
            this.contentObserver.disconnect();
            this.contentObserver = null;
        }
    }
}
