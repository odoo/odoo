import { useRef } from "@web/owl2/utils";
import { Component, onMounted, onWillDestroy, props, t } from "@odoo/owl";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { OVERLAY_SYMBOL } from "@web/core/overlay/overlay_container";
import { usePosition } from "@web/core/position/position_hook";
import { reverseForRTL } from "@web/core/position/utils";
import { useActiveElement } from "@web/core/ui/ui_service";
import { mergeClasses } from "@web/core/utils/classname";
import { useBackButton, useForwardRefToParent } from "@web/core/utils/hooks";

/**
 * @param {EventTarget} target
 * @param {keyof HTMLElementEventMap | keyof WindowEventMap} eventName
 * @param {(ev: Event) => any} handler
 * @param {EventInit} [eventParams]
 */
function useEarlyExternalListener(target, eventName, handler, eventParams) {
    target.addEventListener(eventName, handler, eventParams);
    onWillDestroy(() => target.removeEventListener(eventName, handler, eventParams));
}

/**
 * Will trigger the callback when the window is clicked, giving
 * the clicked element as parameter.
 *
 * This also handles the case where an iframe is clicked.
 *
 * @param {(node?: Node) => any} callback
 * @param {Window} targetWindow
 */
function useClickAway(callback, targetWindow = window) {
    function blurHandler(ev) {
        const target = ev.relatedTarget || targetWindow.document.activeElement;
        if (target?.tagName === "IFRAME") {
            callback(target);
        }
    }

    function navigationHandler() {
        callback(targetWindow.document.documentElement);
    }

    function pointerDownHandler(ev) {
        callback(ev.composedPath()[0]);
    }

    useEarlyExternalListener(targetWindow, "pointerdown", pointerDownHandler, { capture: true });
    useEarlyExternalListener(targetWindow, "blur", blurHandler, { capture: true });
    useEarlyExternalListener(targetWindow, "popstate", navigationHandler, { capture: true });
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

export const popoverProps = {
    // Main props
    component: t.function(),
    componentProps: t.object().optional({}),
    target: t.customValidator(t.any(), (target) => {
        // target may be inside an iframe, so get the Element constructor
        // to test against from its owner document's default view
        const Element = target?.ownerDocument?.defaultView?.Element;
        return (
            (Boolean(Element) && (target instanceof Element || target instanceof window.Element)) ||
            (typeof target === "object" && target?.constructor?.name?.endsWith("Element"))
        );
    }),
    close: t.function(),

    // Styling and semantical props
    animation: t.boolean().optional(true),
    arrow: t.boolean().optional(true),
    class: t.any().optional(""),
    role: t.string().optional(),

    // Positioning props
    fixedPosition: t.boolean().optional(false),
    shrink: t.boolean().optional(),
    holdOnHover: t.boolean().optional(),
    onPositioned: t.function().optional(),
    position: t
        .customValidator(t.string(), (p) => {
            const [d, v = "middle"] = p.split("-");
            return (
                ["top", "bottom", "left", "right"].includes(d) &&
                ["start", "middle", "end", "fit"].includes(v)
            );
        })
        .optional("bottom"),

    // Control props
    closeOnClickAway: t.function().optional(() => () => true),
    closeOnEscape: t.boolean().optional(true),
    setActiveElement: t.boolean().optional(false),

    // Technical props
    ref: t.function().optional(),
    slots: t.object().optional(),
};

export class Popover extends Component {
    static template = "web.Popover";
    props = props(popoverProps);
    static animationTime = 200;

    setup() {
        if (this.props.setActiveElement) {
            useActiveElement("ref");
        }

        useForwardRefToParent("ref");
        this.popoverRef = useRef("ref");
        this.position = usePosition("ref", () => this.props.target, this.positioningOptions);

        const resizeObserver = new ResizeObserver(() => {
            if (!this.props.fixedPosition && (!this.props.animation || this.animationDone)) {
                this.position.unlock();
            }
        });

        onMounted(() => {
            POPOVERS.set(this.props.target, this.popoverRef.el);
            resizeObserver.observe(this.popoverRef.el);
        });
        onWillDestroy(() => POPOVERS.delete(this.props.target));

        if (this.props.target.isConnected) {
            const targetWindow = this.props.target.ownerDocument.defaultView || window;
            useClickAway(this.onClickAway.bind(this), targetWindow);

            if (this.props.closeOnEscape) {
                useHotkey("escape", () => this.props.close());
            }
            const targetObserver = new MutationObserver(this.onTargetMutate.bind(this));
            targetObserver.observe(this.props.target.parentElement, { childList: true });
            onWillDestroy(() => targetObserver.disconnect());
        } else {
            this.props.close();
        }

        useBackButton(
            () => this.props.close(),
            () => this.props.target.isConnected
        );
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
            shrink: this.props.shrink,
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
            this.props.target?.contains(target) ||
            this.popoverRef?.el?.contains(target) ||
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

        // Reverse the direction if RTL as bootstrap expects it that way
        [direction, variant] = reverseForRTL(direction, variant);

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
