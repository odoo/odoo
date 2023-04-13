/** @odoo-module */

import { useThrottleForAnimation } from "./utils/timing";
import { useEffect, useRef } from "@odoo/owl";
import { localization } from "@web/core/l10n/localization";

/**
 * @typedef {(popperElement: HTMLElement, solution: PositioningSolution) => void} PositionEventHandler
 */

/**
 * @typedef {{
 *  popper?: string;
 *  container?: HTMLElement | (() => HTMLElement);
 *  margin?: number;
 *  position?: Direction | Position;
 *  onPositioned?: PositionEventHandler;
 * }} Options
 *
 * @typedef {keyof DirectionsData} DirectionsDataKey
 * @typedef {{
 *  t: number;
 *  b: number;
 *  l: number;
 *  r: number;
 * }} DirectionsData
 *
 * @typedef {keyof VariantsData} VariantsDataKey
 * @typedef {{
 *  vs: number;
 *  vm: number;
 *  ve: number;
 *  hs: number;
 *  hm: number;
 *  he: number;
 * }} VariantsData
 *
 * @typedef {"top" | "left" | "bottom" | "right"} Direction
 * @typedef {"start" | "middle" | "end" | "fit"} Variant
 *
 * @typedef {{[direction in Direction]: string}} DirectionFlipOrder
 *  values are successive DirectionsDataKey represented as a single string
 *
 * @typedef {{[variant in Variant]: string}} VariantFlipOrder
 *  values are successive VariantsDataKey represented as a single string
 *
 * @typedef {`${Direction}-${Variant}`} Position
 *
 * @typedef {{
 *  top: number,
 *  left: number,
 *  direction: Direction,
 *  variant: Variant,
 * }} PositioningSolution
 */

/** @type {{[d: string]: Direction}} */
const DIRECTIONS = { t: "top", r: "right", b: "bottom", l: "left" };
/** @type {{[v: string]: Variant}} */
const VARIANTS = { s: "start", m: "middle", e: "end", f: "fit" };
/** @type DirectionFlipOrder */
const DIRECTION_FLIP_ORDER = { top: "tbrl", right: "rltb", bottom: "btrl", left: "lrbt" };
/** @type VariantFlipOrder */
const VARIANT_FLIP_ORDER = { start: "sme", middle: "mse", end: "ems", fit: "f" };
/** @type DirectionFlipOrder */
const FIT_FLIP_ORDER = { top: "tb", right: "rl", bottom: "bt", left: "lr" };

/** @type {Options} */
const DEFAULTS = {
    popper: "popper",
    margin: 0,
    position: "bottom",
};

/**
 * @param {HTMLElement} el
 * @returns {HTMLIFrameElement?}
 */
function getIFrame(el) {
    const parentDocument = el.ownerDocument.defaultView.parent?.document;
    if (!parentDocument || parentDocument === el.ownerDocument) {
        return;
    }
    return [...parentDocument.getElementsByTagName("iframe")].find((iframe) =>
        iframe.contentDocument.contains(el)
    );
}

/**
 * Returns the best positioning solution staying in the container or falls back
 * to the requested position.
 * The positioning data used to determine each possible position is based on
 * the target, popper, and container sizes.
 * Particularly, a popper must not overflow the container in any direction,
 * it should actually stay at `margin` distance from the border to look good.
 *
 * @param {HTMLElement} target
 * @param {HTMLElement} popper
 * @param {HTMLIFrameElement?} [iframe]
 * @param {Options} options
 * @returns {PositioningSolution} the best positioning solution, relative to
 *                                the containing block of the popper.
 *                                => can be applied to popper.style.(top|left)
 */
function getBestPosition(target, popper, iframe, { container, margin, position }) {
    // Retrieve directions and variants
    const [directionKey, variantKey = "middle"] = position.split("-");
    const directions =
        variantKey === "fit" ? FIT_FLIP_ORDER[directionKey] : DIRECTION_FLIP_ORDER[directionKey];
    const variants = VARIANT_FLIP_ORDER[variantKey];

    // Retrieve container
    if (!container) {
        container = target.ownerDocument.documentElement;
    } else if (typeof container === "function") {
        container = container();
    }

    // Boxes
    const popBox = popper.getBoundingClientRect();
    const targetBox = target.getBoundingClientRect();
    const contBox = container.getBoundingClientRect();
    const iframeBox = iframe?.getBoundingClientRect() || { top: 0, left: 0 };

    const containerIsHTMLNode = container === container.ownerDocument.firstElementChild;

    // Compute positioning data
    /** @type {DirectionsData} */
    const directionsData = {
        t: iframeBox.top + targetBox.top - popBox.height - margin,
        b: iframeBox.top + targetBox.bottom + margin,
        r: iframeBox.left + targetBox.right + margin,
        l: iframeBox.left + targetBox.left - popBox.width - margin,
    };
    /** @type {VariantsData} */
    const variantsData = {
        vf: iframeBox.left + targetBox.left,
        vs: iframeBox.left + targetBox.left,
        vm: iframeBox.left + targetBox.left + targetBox.width / 2 + -popBox.width / 2,
        ve: iframeBox.left + targetBox.right - popBox.width,
        hf: iframeBox.top + targetBox.top,
        hs: iframeBox.top + targetBox.top,
        hm: iframeBox.top + targetBox.top + targetBox.height / 2 + -popBox.height / 2,
        he: iframeBox.top + targetBox.bottom - popBox.height,
    };

    function getPositioningData(d = directions[0], v = variants[0], containerRestricted = false) {
        const vertical = ["t", "b"].includes(d);
        const variantPrefix = vertical ? "v" : "h";
        const directionValue = directionsData[d];
        const variantValue = variantsData[variantPrefix + v];

        if (containerRestricted) {
            const [directionSize, variantSize] = vertical
                ? [popBox.height + margin, popBox.width]
                : [popBox.width, popBox.height + margin];
            let [directionMin, directionMax] = vertical
                ? [contBox.top, contBox.bottom]
                : [contBox.left, contBox.right];
            let [variantMin, variantMax] = vertical
                ? [contBox.left, contBox.right]
                : [contBox.top, contBox.bottom];

            if (containerIsHTMLNode) {
                if (vertical) {
                    directionMin += container.scrollTop;
                    directionMax += container.scrollTop;
                } else {
                    variantMin += container.scrollTop;
                    variantMax += container.scrollTop;
                }
            }

            // Abort if outside container boundaries
            const directionOverflow =
                Math.ceil(directionValue) < Math.floor(directionMin) ||
                Math.floor(directionValue + directionSize) > Math.ceil(directionMax);
            const variantOverflow =
                Math.ceil(variantValue) < Math.floor(variantMin) ||
                Math.floor(variantValue + variantSize) > Math.ceil(variantMax);
            if (directionOverflow || variantOverflow) {
                return null;
            }
        }

        const positioning = vertical
            ? {
                  top: directionValue,
                  left: variantValue,
              }
            : {
                  top: variantValue,
                  left: directionValue,
              };
        return {
            // Subtract the offsets of the containing block (relative to the
            // viewport). It can be done like that because the style top and
            // left were reset to 0px in `reposition`
            // https://developer.mozilla.org/en-US/docs/Web/CSS/Containing_block#identifying_the_containing_block
            top: positioning.top - popBox.top,
            left: positioning.left - popBox.left,
            direction: DIRECTIONS[d],
            variant: VARIANTS[v],
        };
    }

    // Find best solution
    for (const d of directions) {
        for (const v of variants) {
            const match = getPositioningData(d, v, true);
            if (match) {
                // Position match have been found.
                return match;
            }
        }
    }

    // Fallback to default position if no best solution found
    return getPositioningData();
}

/**
 * This method will try to position the popper as requested (according to options).
 * If the requested position does not fit the container, other positions will be
 * tried in different direction and variant flip orders (depending on the requested position).
 * If no position is found that fits the container, the requested position stays used.
 *
 * When the final position is applied, a corresponding CSS class is also added to the popper.
 * This could be used to further styling.
 *
 * @param {HTMLElement} target
 * @param {HTMLElement} popper
 * @param {HTMLIFrameElement} [iframe]
 * @param {Options} options
 */
export function reposition(target, popper, iframe, options) {
    let [directionKey, variantKey = "middle"] = options.position.split("-");
    if (localization.direction === "rtl") {
        if (["bottom", "top"].includes(directionKey)) {
            if (variantKey !== "middle") {
                variantKey = variantKey === "start" ? "end" : "start";
            }
        } else {
            directionKey = directionKey === "left" ? "right" : "left";
        }
    }
    options.position = [directionKey, variantKey].join("-");

    // Reset popper style
    popper.style.position = "fixed";
    popper.style.top = "0px";
    popper.style.left = "0px";

    // Get best positioning solution and apply it
    const position = getBestPosition(target, popper, iframe, options);
    const { top, left, variant } = position;
    popper.style.top = `${top}px`;
    popper.style.left = `${left}px`;

    if (variant === "fit") {
        const styleProperty = ["top", "bottom"].includes(directionKey) ? "width" : "height";
        popper.style[styleProperty] = target.getBoundingClientRect()[styleProperty] + "px";
    }

    if (options.onPositioned) {
        options.onPositioned(popper, position);
    }
}

/**
 * Makes sure that the `popper` element is always
 * placed at `position` from the `target` element.
 * If doing so the `popper` element is clipped off `container`,
 * sensible fallback positions are tried.
 * If all of fallback positions are also clipped off `container`,
 * the original position is used.
 *
 * Note: The popper element should be indicated in your template with a t-ref reference.
 *       This could be customized with the `popper` option.
 *
 * @param {HTMLElement | (() => HTMLElement)} target
 * @param {Options} options
 */
export function usePosition(target, options) {
    const popperRef = useRef(options.popper || DEFAULTS.popper);
    const getTarget = typeof target === "function" ? target : () => target;
    const throttledReposition = useThrottleForAnimation(reposition);
    useEffect(() => {
        const targetEl = getTarget();
        const popperEl = popperRef.el;
        if (!targetEl || !popperEl) {
            return;
        }

        // Prepare
        const targetDocument = targetEl.ownerDocument;
        const iframe = getIFrame(targetEl);
        const currentOptions = { ...DEFAULTS, ...options };

        // Reposition
        reposition(targetEl, popperEl, iframe, currentOptions);

        // Attach listeners to keep the positioning up to date
        const listener = () => throttledReposition(targetEl, popperEl, iframe, currentOptions);
        targetDocument.addEventListener("scroll", listener, { capture: true });
        window.addEventListener("resize", listener);
        return () => {
            targetDocument.removeEventListener("scroll", listener, { capture: true });
            window.removeEventListener("resize", listener);
        };
    });
}
