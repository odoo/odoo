import { Component, useRef, useState, useExternalListener, onMounted, useEffect } from "@odoo/owl";
import { useThrottleForAnimation } from "@web/core/utils/timing";

/**
 * BottomSheetContainer
 *
 * This component is responsible for the overall container of bottom sheets.
 * It uses native browser scroll mechanics rather than transform-based gesture
 * handling. It creates a scrollable overlay where the sheet's position and interactions
 * are controlled through scroll events and scroll-snap points. Advantages:
 *
 * 1. Performance
 *    - Avoids expensive gesture calculations and transform operations
 *    - Utilizes the browser's native scroll optimization and hardware acceleration
 *    - Naturally handles nested scrollable areas through the browser's native scroll-chaining
 *    - Minimizes overhead by delegating motion handling to the browser
 *    - No need for gesture arbitration or delegation logic
 *
 * 4. Accessibility
 *    - Preserves native keyboard navigation
 *    - Make use of the browser's scrolling momentum and bouncing effects
 */

export class BottomSheetContainer extends Component {
    static template = "web.BottomSheetContainer";
    static props = {
        state: { type: Object }
    };

    setup() {
        // Initialize UI state
        this.state = useState({
            isPositionedReady: false,
            progress: -0.5,
        });

        this.containerRef = useRef("container");

        // Mobile browsers adapt the UI according to user interactions
        this.viewportResizeHandler = useThrottleForAnimation(this._computeDimensions.bind(this));
        if (window.visualViewport) {
            useExternalListener(window.visualViewport, "resize", this.viewportResizeHandler);
        }

        this.onScroll = useThrottleForAnimation(this._onScroll.bind(this));

        // React to active sheet changes
        useEffect(
            () => {
                if (this.props.state.activeSheet) {
                    this._computeDimensions();
                    requestAnimationFrame(() => {
                        this._initializePosition();
                    });
                }
            },
            () => [this.props.state.activeSheet?.id, this.props.state.sheetStack.length]
        );

        // Initial setup
        onMounted(() => {
            if (this.props.state.activeSheet) {
                this._computeDimensions();
                this._initializePosition();
            }
        });
    }

    /**
     * Compute dimensions for current active sheet
     * @private
     */
    _computeDimensions() {
        const sheet = this.props.state.activeSheet;
        if (!sheet) return;

        const containerEl = this.containerRef.el;
        if (!containerEl) return;

        const sheetEl = containerEl.querySelector('.o_bottom_sheet_sheet');
        if (!sheetEl) return;

        // Get configuration from the sheet
        const forceExtended = sheet.forceExtendedFullHeight;
        const visibleExtended = sheet.visibleExtended || 90;
        const visibleInitialMax = sheet.visibleInitialMax || 40;

        // Calculate dimensions
        const viewport = {
            get viewportHeight() {
                return window.visualViewport?.height || window.innerHeight;
            }
        };
        const sheetNaturalHeight = this._pxToDvh(sheetEl.scrollHeight);
        const sheetMaxHeight = forceExtended ? 100 : Math.min(sheetNaturalHeight, visibleExtended);
        const sheetVisibleInitial = Math.min(sheetMaxHeight, visibleInitialMax);
        const spacerHeight = this._pxToDvh(viewport.viewportHeight) - sheetVisibleInitial;

        this.isBodyScrollable = sheetNaturalHeight > sheetMaxHeight;

        // Set element dimensions using CSS custom properties
        containerEl.style.setProperty('--sheet-height', forceExtended ? sheetMaxHeight + 'dvh' : 'auto');
        containerEl.style.setProperty('--sheet-max-height', `${sheetMaxHeight}dvh`);
        containerEl.style.setProperty('--spacer-height', `${spacerHeight}dvh`);
        containerEl.style.setProperty('--dismiss-height', `${sheetVisibleInitial}dvh`);

        // Update snapping points
        this.snapPoints = {
            dismiss: 0,
            initial: this._dvhToPx(sheetVisibleInitial),
            max: sheetEl.offsetHeight,
        };
    }

    /**
     * Initialize sheet position
     * @private
     */
    _initializePosition() {
        const containerEl = this.containerRef.el;
        if (!containerEl || !this.snapPoints) return;

        // Set the starting scroll position to the top
        containerEl.scrollTop = (this.snapPoints.initial * 0.5);
        this.state.isPositionedReady = false;
        this._setProgress(-0.5);

        // Scroll to the "initial" position
        containerEl.scroll({ top: this.snapPoints.initial, behavior: "smooth" });
    }

    /**
     * Calculate unified progress value based on scroll position
     * @param {number} scrollTop - Current scroll position
     * @returns {number} progress - Value between -1 and 1
     */
    _calculateProgress(scrollTop) {
        const { initial, max } = this.snapPoints;

        if (scrollTop < initial) {
            // Dismissing: map from [0, initial] to [-1, 0]
            return -1 * (1 - scrollTop / initial);
        } else if (scrollTop > initial) {
            // Extending: map from [initial, max] to [0, 1]
            return Math.min((scrollTop - initial) / (max - initial), 1);
        }

        return 0;
    }

    /**
     * Handle scroll events
     */
    _onScroll() {
        if (!this.containerRef.el || !this.snapPoints || !this.props.state.activeSheet) {
            return;
        }

        const scrollTop = this.containerRef.el.scrollTop;
        const { dismiss, initial, max } = this.snapPoints;
        const threshold = this._dvhToPx(2);

        // Mark as positioned once we reach initial position
        if (!this.state.isPositionedReady && (Math.abs(scrollTop - this.snapPoints.initial) <= threshold)) {
            this.state.isPositionedReady = true;
            this._setProgress(0);
        }

        // Calculate and update progress
        const progress = this._calculateProgress(scrollTop);
        if (progress !== this.state.progress) {
            this._setProgress(progress);

            // Handle position thresholds
            if (this.state.isPositionedReady && !this.props.state.isInitializing &&
                Math.abs(scrollTop - dismiss) <= threshold) {
                // Only remove if ready and not initializing
                return this.remove();
            } else if (Math.abs(scrollTop - initial) <= threshold) {
                // At initial position
                this._setProgress(0);
                if (this.isBodyScrollable) {
                    const bodyEl = this.containerRef.el.querySelector(".offcanvas-body");
                    if (bodyEl) {
                        bodyEl.style.overflow = "hidden";
                        bodyEl.scrollTop = 0;
                    }
                }
            } else if (Math.abs(scrollTop - max) <= threshold) {
                // At max position
                this._setProgress(1);
                if (this.isBodyScrollable) {
                    const bodyEl = this.containerRef.el.querySelector(".offcanvas-body");
                    if (bodyEl) {
                        bodyEl.style.overflow = "auto";
                    }
                }
            }
        }
    }

    /**
     * Start dismissal "animation"
     */
    dismiss() {
        if (!this.containerRef.el) return;
        this.containerRef.el.scroll({ top: 0, behavior: "smooth" });
    }

    /**
     * Close the active sheet
     */
    async remove() {
        this._setProgress(null);

        const activeSheet = this.props.state.activeSheet;
        if (!activeSheet) return;

        if (activeSheet.close) {
            await activeSheet.close();
        }
    }

    /**
     * Set the progress in state and for CSS custom property
     */
    _setProgress(progress) {
        this.state.progress = progress;
        if (this.containerRef.el && (!(progress > 0 && this.snapPoints?.max <= this._dvhToPx(70)))) {
            this.containerRef.el.style.setProperty("--BottomSheet_progress", progress);
        }
    }

    /**
     * Convert between DVH and pixels
     */
    _dvhToPx(dvh) {
        return (dvh * (window.visualViewport?.height || window.innerHeight)) / 100;
    }

    _pxToDvh(pixels) {
        return (pixels * 100) / (window.visualViewport?.height || window.innerHeight);
    }
}