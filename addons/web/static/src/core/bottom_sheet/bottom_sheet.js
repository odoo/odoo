import { Component, useState, useRef, onMounted, useEffect } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useThrottleForAnimation } from "@web/core/utils/timing";
import { compensateScrollbar } from "@web/core/utils/scrolling";

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
        sheetClasses: { type: String, optional: true },
        onClose: { type: Function, optional: true },
        onBack: { type: Function, optional: true },
        slots: { type: Object, optional: true },
        component: { optional: true },
        componentProps: { type: Object, optional: true },
    };

    static defaultProps = {
        title: '',
        showBackBtn: false,
        showCloseBtn: false,
        withBodyPadding: true,
        initialHeightPercent: 50,
        maxHeightPercent: 90,
        startExpanded: false,
        sheetClasses: '',
    };

    setup() {
        this.state = useState({
            isPositionedReady: false,       // Sheet is ready for display
            isExtended: false,              // Sheet is in extended position
            isDismissing: false,            // Sheet is being dismissed
            isSnapping: false,              // Snap behavior enabled
            progress: 0,                    // Visual progress (0-1)
            isInForcedExtendedMode: false   // Track forced extended mode
        });

        // Measurements and configuration (not reactive)
        this.measurements = {
            viewportHeight: 0,
            naturalHeight: 0,
            initialHeight: 0,
            extendedHeight: 0,
            dismissThreshold: 0,
            contentRequiresScrolling: false
        };

        // Snap points for scrolling
        this.snapPoints = {
            dismiss: 0,
            initial: null,
            extended: null
        };

        // References
        this.containerRef = useRef("container");
        this.scrollRailRef = useRef("scrollRail");
        this.sheetRef = useRef("sheet");
        this.sheetBodyRef = useRef("sheetBody");
        this.bottomSheetService = useService("bottomSheet");

        // Create throttled version of scroll handler
        this.throttledOnScroll = useThrottleForAnimation(this.onScroll.bind(this));

        onMounted(() => {
            this.initializeSheet();
            document.body.classList.add("bottom-sheet-open");
            compensateScrollbar(this.scrollRailRef.el, true, true, "padding-right");
        });

        useEffect(() => {
            return () => {
                document.body.classList.remove("bottom-sheet-open");
            };
        }, () => []);
    }

    // Main initialization method
    initializeSheet() {
        if (!this.containerRef.el || !this.scrollRailRef.el || !this.sheetRef.el) return;

        // Step 1: Take measurements
        this.measureDimensions();

        // Step 2: Determine snap points
        this.calculateSnapPoints();

        // Step 3: Apply styles
        this.applyDimensions();

        // Step 4: Set initial position
        this.positionSheet();

        // Step 5: Setup event handlers
        this.setupEventHandlers();

        // Step 6: Mark as ready and enable snap after animation
        this.state.isPositionedReady = true;

        // Wait for CSS animation to complete before enabling snap
        const animationDuration = this.getAnimationDuration('--BottomSheet-slideIn-duration');
        setTimeout(() => {
            this.state.isSnapping = true;
        }, animationDuration);
    }

    // Step 1: Take measurements
    measureDimensions() {
        const viewportHeight = window.innerHeight;

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
            contentRequiresScrolling: naturalHeight > initialHeightPx
        };
    }

    // Step 2: Determine snap points
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

    // Step 3: Apply styles based on measurements and snap points
    applyDimensions() {
        const container = this.containerRef.el;
        const sheet = this.sheetRef.el;
        const { viewportHeight, naturalHeight } = this.measurements;

        // Convert heights to dvh percentages for CSS variables
        const initialHeightPercent = this.snapPoints.initial ?
            (this.snapPoints.initial / viewportHeight * 100) : this.props.initialHeightPercent;

        const maxHeightPercent = this.snapPoints.extended ?
            (this.snapPoints.extended / viewportHeight * 100) : this.props.maxHeightPercent;

        // Set CSS variables for heights
        container.style.setProperty('--sheet-initial-height', `${initialHeightPercent}dvh`);
        container.style.setProperty('--sheet-max-height', `${maxHeightPercent}dvh`);
        container.style.setProperty('--dismiss-height', `${this.snapPoints.initial || 0}px`);

        // Reset max-height to appropriate value
        sheet.style.maxHeight = `${maxHeightPercent}dvh`;

        // Special style considerations
        if (this.props.startExpanded) {
            // Force sheet to extended height if starting expanded
            if (naturalHeight < this.measurements.extendedHeight) {
                sheet.style.minHeight = `${this.props.maxHeightPercent}dvh`;
            }
        } else if (naturalHeight <= this.measurements.initialHeight) {
            // Small content should use natural height
            sheet.style.minHeight = 'auto';
        }
    }

    // Step 4: Set initial position
    positionSheet() {
        const scrollRail = this.scrollRailRef.el;
        const bodyContent = this.sheetBodyRef.el;

        // Determine starting position and scroll value
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

    // Step 5: Setup event handlers
    setupEventHandlers() {
        const scrollRail = this.scrollRailRef.el;
        const bodyContent = this.sheetBodyRef.el;

        // Add scroll event listener
        scrollRail.addEventListener('scroll', this.throttledOnScroll);

        // Handle content scrolling for touch events
        if (bodyContent) {
            bodyContent.addEventListener('touchstart', (e) => {
                if (this.state.isExtended && bodyContent.scrollTop > 0) {
                    e.stopPropagation();
                }
            }, { passive: true });
        }
    }

    // Scroll event handler
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
            }
        }

        // Update content scrolling if position changed
        if (wasExtended !== this.state.isExtended) {
            this.updateContentScrolling(this.state.isExtended);
        }
    }

    // Calculate and update progress value
    updateProgressValue(scrollTop) {
        const { initial, extended } = this.snapPoints;
        let progress = 0;

        if (initial && extended) {
            // Two snap points case
            if (scrollTop <= initial) {
                // 0 to 0.5 range (dismiss to initial)
                progress = (scrollTop / initial) * 0.5;
            } else {
                // 0.5 to 1 range (initial to extended)
                progress = 0.5 + ((scrollTop - initial) / (extended - initial)) * 0.5;
            }
        } else if (initial) {
            // Only initial snap point
            progress = (scrollTop / initial);
        } else if (extended) {
            // Only extended snap point
            progress = (scrollTop / extended);
        }

        // Only update if changed significantly
        if (Math.abs(this.state.progress - progress) > 0.01) {
            this.state.progress = progress;
            this.containerRef.el.style.setProperty('--BottomSheet-progress', progress);
        }
    }

    // Update content scrolling based on extended state
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

    // Snap to a specific position
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

    // Slide out animation
    slideOut() {
        // Prevent duplicate calls
        if (this.state.isDismissing) return;

        // Update state to trigger animation
        this.state.isDismissing = true;
        this.state.isSnapping = false;

        // Get animation duration
        const animationDuration = this.getAnimationDuration('--BottomSheet-slideOut-duration');

        // Wait for animation to complete
        setTimeout(() => {
            if (this.props.id !== undefined) {
                this.bottomSheetService.remove(this.props.id);
            }

            if (this.props.onClose) {
                this.props.onClose();
            }
        }, animationDuration);
    }

    // Get animation duration from CSS variable
    getAnimationDuration(property) {
        if (!this.containerRef.el) return 300;

        const durationStr = getComputedStyle(this.containerRef.el)
            .getPropertyValue(property)
            .trim();

        if (!durationStr) return 300;

        if (durationStr.endsWith('ms')) {
            return parseFloat(durationStr) + 50;
        } else if (durationStr.endsWith('s')) {
            return (parseFloat(durationStr) * 1000) + 50;
        }

        return parseFloat(durationStr) || 300;
    }

    // Public API methods
    expandSheet() {
        if (this.snapPoints.extended) {
            this.snapToPosition('extended');
        }
    }

    collapseSheet() {
        if (this.snapPoints.initial) {
            this.snapToPosition('initial');
        } else {
            this.slideOut();
        }
    }

    close() {
        this.slideOut();
    }

    back() {
        if (this.props.onBack) {
            this.props.onBack();
        } else {
            this.slideOut();
        }
    }
}
