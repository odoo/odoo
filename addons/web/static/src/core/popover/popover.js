import { Component, onMounted, onWillDestroy, useExternalListener, useRef } from "@odoo/owl";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { OVERLAY_SYMBOL } from "@web/core/overlay/overlay_container";
import { usePosition } from "@web/core/position/position_hook";
import { useActiveElement } from "@web/core/ui/ui_service";
import { mergeClasses } from "@web/core/utils/classname";
import { useForwardRefToParent } from "@web/core/utils/hooks";

/**
 * Will trigger the callback when the window is clicked, giving
 * the clicked element as parameter.
 *
 * This also handles the case where an iframe is clicked.
 *
 * @param {Function} callback
 */
function useClickAway(callback) {
    const pointerDownHandler = (event) => {
        callback(event.composedPath()[0]);
    };

    const blurHandler = (ev) => {
        const target = ev.relatedTarget || document.activeElement;
        if (target?.tagName === "IFRAME") {
            callback(target);
        }
    };

    useExternalListener(window, "pointerdown", pointerDownHandler, { capture: true });
    useExternalListener(window, "blur", blurHandler, { capture: true });
}

const POPOVERS = new WeakMap();
/**
 * Can be used to retrieve the popover element for a given target.
 * @param {HTMLElement} target
 * @returns {HTMLElement | undefined} the popover element if it exists
 */
export function getPopoverForTarget(target) {
    return POPOVERS.get(target);
}

export class Popover extends Component {
    static template = "web.Popover";
    static defaultProps = {
        animation: true,
        arrow: true,
        class: "",
        closeOnClickAway: () => true,
        closeOnEscape: true,
        componentProps: {},
        fixedPosition: false,
        position: "bottom",
        setActiveElement: false,
    };
    static props = {
        // Main props
        component: { type: Function },
        componentProps: { optional: true, type: Object },
        target: {
            validate: (target) => {
                // target may be inside an iframe, so get the Element constructor
                // to test against from its owner document's default view
                const Element = target?.ownerDocument?.defaultView?.Element;
                return (
                    (Boolean(Element) &&
                        (target instanceof Element || target instanceof window.Element)) ||
                    (typeof target === "object" && target?.constructor?.name?.endsWith("Element"))
                );
            },
        },

        // Styling and semantical props
        animation: { optional: true, type: Boolean },
        arrow: { optional: true, type: Boolean },
        class: { optional: true },
        role: { optional: true, type: String },

        // Positioning props
        fixedPosition: { optional: true, type: Boolean },
        holdOnHover: { optional: true, type: Boolean },
        onPositioned: { optional: true, type: Function },
        position: {
            optional: true,
            type: String,
            validate: (p) => {
                const [d, v = "middle"] = p.split("-");
                return (
                    ["top", "bottom", "left", "right"].includes(d) &&
                    ["start", "middle", "end", "fit"].includes(v)
                );
            },
        },

        // Control props
        close: { optional: true, type: Function },
        closeOnClickAway: { optional: true, type: Function },
        closeOnEscape: { optional: true, type: Boolean },
        setActiveElement: { optional: true, type: Boolean },

        // Technical props
        ref: { optional: true, type: Function },
        slots: { optional: true, type: Object },
    };
    static animationTime = 200;

    setup() {
        if (this.props.setActiveElement) {
            useActiveElement("ref");
        }

        useForwardRefToParent("ref");
        this.popoverRef = useRef("ref");
        this.position = usePosition("ref", () => this.props.target, this.positioningOptions);

        if (this.props.target.isConnected) {
            useClickAway((target) => this.onClickAway(target));

            if (this.props.closeOnEscape) {
                useHotkey("escape", () => this.props.close());
            }
            const targetObserver = new MutationObserver(this.onTargetMutate.bind(this));
            targetObserver.observe(this.props.target.parentElement, { childList: true });
            onWillDestroy(() => targetObserver.disconnect());
        } else {
            this.props.close();
        }
        onMounted(() => POPOVERS.set(this.props.target, this.popoverRef.el));
        onWillDestroy(() => POPOVERS.delete(this.props.target));
    }

    get defaultClassObj() {
        return mergeClasses("o_popover popover mw-100 bs-popover-auto", this.props.class);
    }

    get positioningOptions() {
        return {
            margin: this.props.arrow ? 8 : 0,
            onPositioned: (el, solution) => {
                this.onPositioned(solution);
                this.props.onPositioned?.(el, solution);
            },
            position: this.props.position,
        };
    }

    animate(direction) {
        const transform = {
            top: ["translateY(-5%)", "translateY(0)"],
            right: ["translateX(5%)", "translateX(0)"],
            bottom: ["translateY(5%)", "translateY(0)"],
            left: ["translateX(-5%)", "translateX(0)"],
        }[direction];
        return this.popoverRef.el.animate(
            { opacity: [0, 1], transform },
            this.constructor.animationTime
        );
    }

    isInside(target) {
        return (
            this.props.target.contains(target) ||
            this.popoverRef.el.contains(target) ||
            this.env[OVERLAY_SYMBOL]?.contains(target)
        );
    }

    onClickAway(target) {
        if (this.props.closeOnClickAway(target) && !this.isInside(target)) {
            this.props.close();
        }
    }

    onPositioned({ direction, variant, variantOffset }) {
        if (this.props.arrow) {
            this.updateArrow(direction, variant, variantOffset);
        }

        // opening animation (only once)
        if (this.props.animation && !this.animationDone) {
            this.position.lock();
            this.animate(direction).finished.then(() => {
                this.animationDone = true;
                if (!this.props.fixedPosition) {
                    this.position.unlock();
                }
            });
        }

        if (this.props.fixedPosition) {
            // Prevent further positioning updates if fixed position is wanted
            this.position.lock();
        }
    }

    onTargetMutate() {
        if (!this.props.target.isConnected) {
            this.props.close();
        }
    }

    updateArrow(direction, variant, variantOffset) {
        const { el } = this.popoverRef;

        // Update the bootstrap popper placement, in order to give the arrow its shape
        el.dataset.popperPlacement = direction;

        // Update arrow position
        const vertical = ["top", "bottom"].includes(direction);
        const placementProperty = vertical ? "left" : "top";
        const placement = {
            start: "--position-min",
            middle: "--position-center",
            fit: "--position-center",
            end: "--position-max",
        }[variant];
        const arrowEl = el.querySelector(":scope > .popover-arrow");
        Object.assign(arrowEl.style, {
            top: "",
            left: "",
            [placementProperty]: `clamp(
                var(--position-min),
                calc(var(${placement}) - ${variantOffset}px),
                var(--position-max)
            )`,
        });

        // Should the arrow get sucked?
        const sizeProperty = vertical ? "width" : "height";
        const { [sizeProperty]: arrowSize, [placementProperty]: arrowPosition } =
            arrowEl.getBoundingClientRect();
        const { [sizeProperty]: targetSize, [placementProperty]: targetPosition } =
            this.props.target.getBoundingClientRect();
        const arrowCenter = arrowPosition + arrowSize / 2;
        const margin = arrowSize / 2 - 1;
        const hasEnoughSpace = arrowSize < targetSize - 2 * margin;
        const isOutsideSafeEdge =
            arrowCenter < targetPosition + margin ||
            arrowCenter > targetPosition + targetSize - margin;
        arrowEl.classList.toggle("sucked", hasEnoughSpace && isOutsideSafeEdge);
    }
}
