import { Component, useChildSubEnv, useState, useExternalListener, onMounted } from "@odoo/owl";
import { useForwardRefToParent } from "@web/core/utils/hooks";
import { useActiveElement } from "../ui/ui_service";
import { useThrottleForAnimation, useDebounced } from "@web/core/utils/timing";

/**
 * BottomSheet
 *
 * This component uses native browser scroll mechanics rather than transform-based gesture
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

export class BottomSheet extends Component {
    static template = "web.BottomSheet";
    static props = {
        sheetClasses: { type: String, optional: true },
        bodyClass: { type: String, optional: true },
        footer: { type: Boolean, optional: true },
        header: { type: Boolean, optional: true },
        showCloseBtn: { type: Boolean, optional: true },
        showBackBtn: { type: Boolean, optional: true },
        title: { type: String, optional: true },
        bottomSheetRootRef: { type: Function, optional: true },
        slots: {
            type: Object,
            shape: {
                default: Object,
                header: { type: Object, optional: true },
                footer: { type: Object, optional: true },
            },
        },
        cancel: { type: Function, optional: true },
        close: { type: Function, optional: true },
        back: { type: Function, optional: true },
        withBodyPadding: { type: Boolean, optional: true },
        visibleInitialMax: { type: Number, optional: true },
        visibleExtended: { type: Number, optional: true },
        forceExtendedFullHeight: { type: Boolean, optional: true },
    };

    static defaultProps = {
        withBodyPadding: true,
        visibleInitialMax: 40,
        visibleExtended: 90,
    };

    setup() {
        this.bottomSheetRootRef = useForwardRefToParent("bottomSheetRootRef");
        useActiveElement("bottomSheetRootRef");

        // Initialize state
        this.state = useState({
            isPositionedReady: false,
            progress: -0.5,
        });

        this.data = useState(this.env.bottomSheetData || {
            id: 0,
            isActive: true,
            close: () => {},
            dismiss: () => {},
            back: () => {},
        });

        this.id = `o_bottom_sheet_${this.data.id}`;
        useChildSubEnv({ inBottomSheet: true, bottomSheetId: this.id });

        // Mobile browsers adapt the UI according to user interactions (eg. keyboard appears
        // or the browser's bar hide).
        // Detect these scenario on visualViewport resize and compute the actual dimensions
        // using dynamic viewport size units.
        //
        // https://developer.mozilla.org/en-US/docs/Web/API/VisualViewport
        // https://www.w3.org/TR/css-values-4/#dynamic-viewport-size
        this.viewportResizeHandler = useThrottleForAnimation(this._computeDimensions.bind(this));
        if (window.visualViewport) {
            useExternalListener(window.visualViewport, "resize", this.viewportResizeHandler);
        }

        this.onScrollDebounced = useThrottleForAnimation(this._onScroll);

        onMounted(() => {
            this._computeDimensions();
            this._initializePosition();

            // If scrollEnd event is not supported (Safari), use the debounced handler.
            // https://developer.mozilla.org/en-US/docs/Web/API/Element/scrollend_event#browser_compatibility
            this.hasNativeScrollEnd = 'onscrollend' in window;
            if (!this.hasNativeScrollEnd) {
                this.onScrollEndDebounced = useDebounced( this.onScrollEnd.bind(this), 100, { execBeforeUnmount: false });
                this.bottomSheetRootRef.el.addEventListener('scroll', () => {
                    this.state.isDebouncedScrollEnd = true;
                    this.onScrollEndDebounced({ target: this.bottomSheetRootRef.el });
                });
            }
        });
    }

    /**
     * Compute dimensions
     * https://www.w3.org/TR/css-values-4/#dynamic-viewport-size
     * @private
     */
    _computeDimensions() {
        const forceFull = this.props.forceExtendedFullHeight;
        const viewport = {
            get viewportHeight() {
                return window.visualViewport?.height || window.innerHeight;
            }
        };
        const sheetEl = this.bottomSheetRootRef.el.querySelector('.o_bottom_sheet_sheet');
        const sheetNaturalHeight = this._pxToDvh(sheetEl.scrollHeight);
        const sheetMaxHeight = forceFull ? 100 : Math.min(sheetNaturalHeight, this.props.visibleExtended);
        const sheetVisibleInitial = Math.min(sheetMaxHeight, this.props.visibleInitialMax);
        const spacerHeight = this._pxToDvh(viewport.viewportHeight) - sheetVisibleInitial;

        this.isBodyScrollable = sheetNaturalHeight > sheetMaxHeight;

        // Set element dimensions using CSS custom properties
        this.bottomSheetRootRef.el.style.setProperty('--sheet-height', forceFull ? sheetMaxHeight + 'dvh' : 'auto');
        this.bottomSheetRootRef.el.style.setProperty('--sheet-max-height', `${sheetMaxHeight}dvh`);
        this.bottomSheetRootRef.el.style.setProperty('--spacer-height', `${spacerHeight}dvh`);
        this.bottomSheetRootRef.el.style.setProperty('--dismiss-height', `${sheetVisibleInitial}dvh`);

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
        // Set the starting scroll position to the top.
        this.bottomSheetRootRef.el.scrollTop = (this.snapPoints.initial * 0.5);
        // this.bottomSheetRootRef.el.scroll({top: this.snapPoints.initial * 0.5, behavior: "instant" });
        this.state.isPositionedReady = false;
        this._setProgress(-0.5);

        // Scroll to the "initial" position
        this.bottomSheetRootRef.el.scroll({ top: this.snapPoints.initial, behavior: "smooth" });
    }

    /**
     * Calculate unified progress value based on scroll position
     * @param {number} scrollTop - Current scroll position
     * @returns {number} progress - Value between -1 and 1
     *   -1 to 0: dismissing (0 = initial position, -1 = fully dismissed)
     *    0 to 1: extending (0 = initial position, 1 = fully extended)
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

        // At initial position
        return 0;
    }

    _onScroll(ev) {
        if (!this.data.isActive) {
            return;
        }

        const scrollTop = this.bottomSheetRootRef.el.scrollTop;

        if ((Math.abs(scrollTop - this.snapPoints.initial) <= this._dvhToPx(2)) && !this.state.isPositionedReady) {
            this.state.isPositionedReady = true;
            // Initialize progress to 0 (neutral position)
            this._setProgress(0);
        }

        const progress = this._calculateProgress(scrollTop);

        if (progress !== this.state.progress) {
            this._setProgress(progress);
        }
    }

    /**
     * Handle scroll end with updated snap points
     * @private
     */
    onScrollEnd (ev) {
        // Make sure we only handle scroll events for the active sheet
        if (!this.data.isActive) {
            return;
        }

        const scrollTop = this.bottomSheetRootRef.el.scrollTop;
        const { dismiss, initial, max } = this.snapPoints;
        const threshold = this._dvhToPx(2);


        // if (this.state.isPositionedReady) {
            if (Math.abs(scrollTop - dismiss) <= threshold) {
                return this.remove();
            } else if (Math.abs(scrollTop - initial) <= threshold) {
                // At initial position - reset progress
                this._setProgress(0);
                if (this.isBodyScrollable) {
                    this.bottomSheetRootRef.el.querySelector(".offcanvas-body").style.overflow = "hidden";
                    this.bottomSheetRootRef.el.querySelector(".offcanvas-body").scrollTop = 0;
                }
            } else if (Math.abs(scrollTop - max) <= threshold) {
                // At max position - ensure progress is 1
                this._setProgress(1);
                if (this.isBodyScrollable) {
                    this.bottomSheetRootRef.el.querySelector(".offcanvas-body").style.overflow = "auto";
                }
            }
        // }

        // Reset Safari scrollEnd debounced flag
        if (!this.hasNativeScrollEnd) {
            this.state.isDebouncedScrollEnd = false;
        }
    }

    /**
     * Dismiss the bottom sheet
     */
    dismiss() {
        this.bottomSheetRootRef.el.scroll({ top: 0, behavior: "smooth" });
    }

    /**
     * Remove the bottom sheet
     */
    async remove() {
        // Set progress null to indicate removal is underway
        this._setProgress(null);
    
        // Call dismiss handlers
        try {
            if (this.data.close) {
                await this.data.close();
            }
            if (this.data.dismiss) {
                await this.data.dismiss();
            }
        } catch (error) {
            console.error("Error during bottom sheet dismiss:", error);
            // Still try to remove the sheet even if handlers fail
            if (this.props.close) {
                this.props.close();
            }
        }
    }

    // Utils

    /**
     * Set the progress in state and for CSS custom property
     * @param {number} progress - Dynamic viewport height units
     */
    _setProgress(progress) {
        this.state.progress = progress;

        // Avoid performing background animations if the sheet will never reach a reasonable size
        if (!(progress > 0 && this.snapPoints.max <= this._dvhToPx(70))) {
            this.bottomSheetRootRef.el.style.setProperty("--BottomSheet_progress", progress);
            // document.body.style.setProperty("--BottomSheet_progress", progress);
        }
    }

    /**
     * Get the actual pixel value from a CSS dynamic viewport height value
     * @param {number} dvh - Dynamic viewport height units
     * @returns {number} Actual pixels
     */
    _dvhToPx(dvh) {
        return (dvh * (window.visualViewport?.height || window.innerHeight)) / 100;
    }

    /**
     * Convert pixels to dynamic viewport height (dvh) units
     * @param {number} pixels - Value in pixels to convert
     * @returns {number} Value in dvh units
     */
    _pxToDvh(pixels) {
        return (pixels * 100) / (window.visualViewport?.height || window.innerHeight);
    }
}
