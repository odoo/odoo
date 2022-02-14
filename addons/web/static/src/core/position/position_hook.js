/** @odoo-module */

import { throttleForAnimation } from "../utils/timing";

const { onWillUnmount, useEffect, useExternalListener, useRef } = owl;

/**
 * @typedef {{
 *  popper?: string;
 *  container?: HTMLElement;
 *  margin?: number;
 *  position?: Position;
 *  classes?: Partial<ClassNames>;
 * }} Options
 *
 * @typedef {{[position in Position?]: string}} ClassNames
 *
 * @typedef {{
 *  directions: (DirectionsDataKey)[];
 *  variants: (VariantsDataKey)[];
 *  get: (d?: DirectionsDataKey, v?: VariantsDataKey, containerRestricted?: boolean) => (()=>void)?;
 * }} Positioning
 *  `get` may return a function that will apply the style to the popper when called
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
 * @typedef {"start" | "middle" | "end"} Variant
 *
 * @typedef {{[direction in Direction]: string}} DirectionFlipOrder
 *  values are successive DirectionsDataKey represented as a single string
 *
 * @typedef {{[variant in Variant]: string}} VariantFlipOrder
 *  values are successive VariantsDataKey represented as a single string
 *
 * @typedef {Direction
 *  | "top-start" | "top-middle" | "top-end"
 *  | "left-start" | "left-middle" | "left-end"
 *  | "right-start" | "right-middle" | "right-end"
 *  | "bottom-start" | "bottom-middle" | "bottom-end"} Position
 */

/** @type DirectionFlipOrder */
const DIRECTION_FLIP_ORDER = { top: "tbrl", right: "rltb", bottom: "btrl", left: "lrbt" };
/** @type VariantFlipOrder */
const VARIANT_FLIP_ORDER = { start: "sme", middle: "mse", end: "ems" };

/** @type {Partial<Options>} */
const DEFAULTS = {
    popper: "popper",
    margin: 0,
    position: "bottom",
    classes: {
        "top-start": "o-popper-position--ts",
        "top-middle": "o-popper-position--tm",
        "top-end": "o-popper-position--te",
        "right-start": "o-popper-position--rs",
        "right-middle": "o-popper-position--rm",
        "right-end": "o-popper-position--re",
        "bottom-start": "o-popper-position--bs",
        "bottom-middle": "o-popper-position--bm",
        "bottom-end": "o-popper-position--be",
        "left-start": "o-popper-position--ls",
        "left-middle": "o-popper-position--lm",
        "left-end": "o-popper-position--le",
    },
};

/**
 * Computes positioning data used to determine each possible position
 * based on the reference, popper, and container sizes.
 * Particularly, a popper must not overflow the container in any direction,
 * it should actually stay at `margin` distance from the border to look good.
 *
 * @param {HTMLElement} reference
 * @param {HTMLElement} popper
 * @returns {Positioning} a positioning object containing:
 *  - ascendingly sorted directions and variants
 *  - a method returning style to apply to the popper for a given direction and variant
 */
function computePositioning(reference, popper, options) {
    const { container, margin, position, classes } = options;

    // Retrieve directions and variants
    const [direction, variant = "middle"] = position.split("-");
    const directions = DIRECTION_FLIP_ORDER[direction];
    const variants = VARIANT_FLIP_ORDER[variant];

    // Boxes
    const popBox = popper.getBoundingClientRect();
    const refBox = reference.getBoundingClientRect();
    const contBox = container.getBoundingClientRect();

    const containerIsHTMLNode = container === document.firstElementChild;

    // Compute positioning data
    /** @type {DirectionsData} */
    const directionsData = {
        t: refBox.top - popBox.height - margin,
        b: refBox.bottom + margin,
        r: refBox.right + margin,
        l: refBox.left - popBox.width - margin,
    };
    /** @type {VariantsData} */
    const variantsData = {
        vs: refBox.left,
        vm: refBox.left + refBox.width / 2 + -popBox.width / 2,
        ve: refBox.right - popBox.width,
        hs: refBox.top,
        hm: refBox.top + refBox.height / 2 + -popBox.height / 2,
        he: refBox.bottom - popBox.height,
    };

    function get(d = directions[0], v = variants[0], containerRestricted = false) {
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
                Math.ceil(directionValue) < Math.ceil(directionMin) ||
                Math.ceil(directionValue + directionSize) > Math.ceil(directionMax);
            const variantOverflow =
                Math.ceil(variantValue) < Math.ceil(variantMin) ||
                Math.ceil(variantValue + variantSize) > Math.ceil(variantMax);
            if (directionOverflow || variantOverflow) {
                return null;
            }
        }

        const { top, left } = vertical
            ? {
                  top: directionValue,
                  left: variantValue,
              }
            : {
                  top: variantValue,
                  left: directionValue,
              };

        return () => {
            popper.style.top = `${top}px`;
            popper.style.left = `${left}px`;
            for (const [position, className] of Object.entries(classes)) {
                const [direction, variant] = position.split("-");
                if (direction.startsWith(d) && (!variant || variant.startsWith(v))) {
                    popper.classList.add(className);
                }
            }
        };
    }

    return {
        directions,
        variants,
        get,
    };
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
 * @param {HTMLElement} reference
 * @param {HTMLElement} popper
 * @param {Options} options
 */
function reposition(reference, popper, options) {
    options = {
        container: document.documentElement,
        ...options,
    };

    // Reset popper style
    const classNames = Object.values(options.classes);
    popper.classList.remove(...classNames);
    popper.style.position = "fixed";
    popper.style.top = "0";
    popper.style.left = "0";

    // Compute positioning and find first match
    const positioning = computePositioning(reference, popper, options);

    let position;
    loops: {
        for (const d of positioning.directions) {
            for (const v of positioning.variants) {
                position = positioning.get(d, v, true);
                if (position) {
                    // A position match have been found.
                    break loops;
                }
            }
        }
    }
    // fallback to given `position` if nothing matches
    (position || positioning.get())();
}

/**
 * Makes sure that the `popper` element is always
 * placed at `position` from the `reference` element.
 * If doing so the `popper` element is clipped off `container`,
 * sensible fallback positions are tried.
 * If all of fallback positions are also clipped off `container`,
 * the original position is used.
 *
 * Note: The popper element should be indicated in your template with a t-ref reference.
 *       This could be customized with the `popper` option.
 *
 * @param {HTMLElement | (()=>HTMLElement)} reference
 * @param {Options} options
 */
export function usePosition(reference, options) {
    options = { ...DEFAULTS, ...options };
    const { popper } = options;
    const popperRef = useRef(popper);
    const getReference = reference instanceof HTMLElement ? () => reference : reference;
    const update = () => {
        const ref = getReference();
        if (popperRef.el && ref) {
            reposition(ref, popperRef.el, options);
        }
    };
    useEffect(update);
    const throttledUpdate = throttleForAnimation(update);
    useExternalListener(document, "scroll", throttledUpdate, { capture: true });
    useExternalListener(window, "resize", throttledUpdate);
    onWillUnmount(throttledUpdate.cancel);
}
