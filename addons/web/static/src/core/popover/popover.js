import { Component, onMounted, onWillDestroy, useComponent, useRef } from "@odoo/owl";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { OVERLAY_SYMBOL } from "@web/core/overlay/overlay_container";
import { usePosition } from "@web/core/position/position_hook";
import { useActiveElement } from "@web/core/ui/ui_service";
import { addClassesToElement, mergeClasses } from "@web/core/utils/classname";
import { useForwardRefToParent } from "@web/core/utils/hooks";

function useEarlyExternalListener(target, eventName, handler, eventParams) {
    const component = useComponent();
    const boundHandler = handler.bind(component);
    target.addEventListener(eventName, boundHandler, eventParams);
    onWillDestroy(() => target.removeEventListener(eventName, boundHandler, eventParams));
}

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

    useEarlyExternalListener(window, "pointerdown", pointerDownHandler, { capture: true });
    useEarlyExternalListener(window, "blur", blurHandler, { capture: true });
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

        let shouldAnimate = this.props.animation;
        this.position = usePosition("ref", () => this.props.target, {
            onPositioned: (el, solution) => {
                (this.props.onPositioned || this.onPositioned.bind(this))(el, solution);
                if (this.props.arrow && this.props.onPositioned) {
                    this.onPositioned.bind(this)(el, solution);
                }

                // opening animation
                if (shouldAnimate) {
                    shouldAnimate = false; // animate only once
                    const transform = {
                        top: ["translateY(-5%)", "translateY(0)"],
                        right: ["translateX(5%)", "translateX(0)"],
                        bottom: ["translateY(5%)", "translateY(0)"],
                        left: ["translateX(-5%)", "translateX(0)"],
                    }[solution.direction];
                    this.position.lock();
                    const animation = el.animate(
                        { opacity: [0, 1], transform },
                        this.constructor.animationTime
                    );
                    animation.finished.then(this.position.unlock);
                }

                if (this.props.fixedPosition) {
                    // Prevent further positioning updates if fixed position is wanted
                    this.position.lock();
                }
            },
            position: this.props.position,
        });

        onMounted(() => POPOVERS.set(this.props.target, this.popoverRef.el));
        onWillDestroy(() => POPOVERS.delete(this.props.target));

        if (!this.props.close) {
            return;
        }
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
    }

    get defaultClassObj() {
        return mergeClasses(
            "o_popover popover mw-100",
            { "o-popover--with-arrow": this.props.arrow },
            this.props.class
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

    onTargetMutate() {
        if (!this.props.target.isConnected) {
            this.props.close();
        }
    }

    onPositioned(el, { direction, variant }) {
        const position = `${direction[0]}${variant[0]}`;

        // reset all popover classes
        el.classList = [];
        const directionMap = {
            top: "top",
            bottom: "bottom",
            left: "start",
            right: "end",
        };
        addClassesToElement(
            el,
            this.defaultClassObj,
            `bs-popover-${directionMap[direction]}`,
            `o-popover-${direction}`,
            `o-popover--${position}`
        );

        if (this.props.arrow) {
            const arrowEl = el.querySelector(":scope > .popover-arrow");
            // reset all arrow classes
            arrowEl.className = "popover-arrow";
            switch (position) {
                case "tm": // top-middle
                case "bm": // bottom-middle
                case "tf": // top-fit
                case "bf": // bottom-fit
                    arrowEl.classList.add("start-0", "end-0", "mx-auto");
                    break;
                case "lm": // left-middle
                case "rm": // right-middle
                case "lf": // left-fit
                case "rf": // right-fit
                    arrowEl.classList.add("top-0", "bottom-0", "my-auto");
                    break;
                case "ts": // top-start
                case "bs": // bottom-start
                    arrowEl.classList.add("end-auto");
                    break;
                case "te": // top-end
                case "be": // bottom-end
                    arrowEl.classList.add("start-auto");
                    break;
                case "ls": // left-start
                case "rs": // right-start
                    arrowEl.classList.add("bottom-auto");
                    break;
                case "le": // left-end
                case "re": // right-end
                    arrowEl.classList.add("top-auto");
                    break;
            }
        }
    }
}
