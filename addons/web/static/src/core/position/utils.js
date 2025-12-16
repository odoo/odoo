import { localization } from "@web/core/l10n/localization";

/**
 * @typedef {"top" | "left" | "bottom" | "right"} Direction
 * @typedef {"start" | "middle" | "end" | "fit"} Variant
 *
 * @typedef {{[direction in Direction]: string}} DirectionFlipOrder
 *  string values should match regex /^[tbrl]+$/m
 *
 * @typedef {{[variant in Variant]: string}} VariantFlipOrder
 *  string values should match regex /^[smef]+$/m
 *
 * @typedef {{
 *  top: number,
 *  left: number,
 *  maxHeight?: number;
 *  direction: Direction,
 *  variant: Variant,
 *  variantOffset?: number,
 * }} PositioningSolution
 *
 * @typedef ComputePositionOptions
 * @property {HTMLElement | () => HTMLElement} [container] container element
 * @property {number} [margin=0]
 *  margin in pixels between the popper and the target.
 * @property {Direction | `${Direction}-${Variant}`} [position="bottom"]
 *  position of the popper relative to the target
 * @property {boolean} [flip=true]
 *  allow the popper to try a flipped direction when it overflows the container
 * @property {boolean} [extendedFlipping=false]
 *  allow the popper to try for all possible flipping directions (including center)
 *  when it overflows the container
 * @property {boolean} [shrink=false]
 *  reduce the popper's height when it overflows the container
 */

/** @type {ComputePositionOptions} */
const DEFAULTS = {
    flip: true,
    margin: 0,
    position: "bottom",
};

/** @type {{[d: string]: Direction}} */
const DIRECTIONS = { t: "top", r: "right", b: "bottom", l: "left", c: "center" };
/** @type {{[v: string]: Variant}} */
const VARIANTS = { s: "start", m: "middle", e: "end", f: "fit" };
/** @type DirectionFlipOrder */
const DIRECTION_FLIP_ORDER = { top: "tb", right: "rl", bottom: "bt", left: "lr", center: "c" };
/** @type DirectionFlipOrder */
const EXTENDED_DIRECTION_FLIP_ORDER = {
    top: "tbrlc",
    right: "rlbtc",
    bottom: "btrlc",
    left: "lrbtc",
    center: "c",
};
/** @type VariantFlipOrder */
const VARIANT_FLIP_ORDER = { start: "se", middle: "m", end: "es", fit: "f" };

/**
 * @param {HTMLElement} popperEl
 * @param {HTMLElement} targetEl
 * @returns {HTMLIFrameElement?}
 */
function getIFrame(popperEl, targetEl) {
    return [...popperEl.ownerDocument.getElementsByTagName("iframe")].find((iframe) =>
        iframe.contentDocument?.contains(targetEl)
    );
}

/**
 * Returns the RTl adapted direction and variant if needed.
 * If the current localization direction is "rtl":
 *  - Direction "left" and "right" are flipped to "right" and "left".
 *  - Variant "start" and "end" are flipped to "end" and "start".
 *
 * @param {Direction} direction
 * @param {Variant} [variant="middle"] (default value is "middle")
 * @returns {[Direction, Variant]}
 */
export function reverseForRTL(direction, variant = "middle") {
    if (localization.direction === "rtl") {
        if (["left", "right"].includes(direction)) {
            direction = direction === "left" ? "right" : "left";
        } else if (["start", "end"].includes(variant)) {
            // here direction is either "top" or "bottom"
            variant = variant === "start" ? "end" : "start";
        }
    }
    return [direction, variant];
}

/**
 * Returns the best positioning solution staying in the container or falls back
 * to the requested position.
 * The positioning data used to determine each possible position is based on
 * the target, popper, and container sizes.
 * Particularly, a popper must not overflow the container in any direction.
 * The popper will stay at `margin` distance from its target. One could also
 * use the CSS margins of the popper element to achieve the same result.
 *
 * Pre-condition: the popper element must have a fixed positioning
 *                with top and left set to 0px.
 *
 * @param {HTMLElement} popper
 * @param {HTMLElement} target
 * @param {ComputePositionOptions} options
 * @returns {PositioningSolution} the best positioning solution, relative to
 *                                the containing block of the popper.
 *                                => can be applied to popper.style.(top|left)
 */
function computePosition(
    popper,
    target,
    { container, extendedFlipping, flip, margin, position, shrink }
) {
    // Retrieve directions and variants
    const [direction, variant = "middle"] = reverseForRTL(...position.split("-"));
    let directions = [direction.at(0)];
    if (flip) {
        directions = extendedFlipping
            ? EXTENDED_DIRECTION_FLIP_ORDER[direction]
            : DIRECTION_FLIP_ORDER[direction];
    }
    const variants = VARIANT_FLIP_ORDER[variant];

    // Retrieve container
    if (!container) {
        container = popper.ownerDocument.documentElement;
    } else if (typeof container === "function") {
        container = container();
    }

    if (variant === "fit") {
        // make sure the popper has the desired dimensions during the computation of the position
        const styleProperty = ["top", "bottom"].includes(direction) ? "width" : "height";
        popper.style[styleProperty] = getComputedStyle(target)[styleProperty];
    }

    // Account for popper actual margins
    const popperStyle = getComputedStyle(popper);
    const { marginTop, marginLeft, marginRight, marginBottom } = popperStyle;
    const popMargins = {
        top: parseFloat(marginTop),
        left: parseFloat(marginLeft),
        right: parseFloat(marginRight),
        bottom: parseFloat(marginBottom),
    };

    // IFrame
    const shouldAccountForIFrame = popper.ownerDocument !== target.ownerDocument;
    const iframe = shouldAccountForIFrame ? getIFrame(popper, target) : null;

    // Boxes
    const popBox = popper.getBoundingClientRect();
    const targetBox = target.getBoundingClientRect();
    const contBox = container.getBoundingClientRect();
    const iframeBox = iframe?.getBoundingClientRect() ?? { top: 0, left: 0 };

    const containerIsHTMLNode = container === container.ownerDocument.firstElementChild;
    const containerIsInIframe =
        shouldAccountForIFrame && target.ownerDocument === container.ownerDocument;

    // Compute positioning data
    const directionsData = {
        t: iframeBox.top + targetBox.top - popMargins.bottom - margin - popBox.height,
        b: iframeBox.top + targetBox.bottom + popMargins.top + margin,
        r: iframeBox.left + targetBox.right + popMargins.left + margin,
        l: iframeBox.left + targetBox.left - popMargins.right - margin - popBox.width,
        c: iframeBox.top + targetBox.top + targetBox.height / 2 - popBox.height / 2,
    };
    const variantsData = {
        vf: iframeBox.left + targetBox.left,
        vs: iframeBox.left + targetBox.left + popMargins.left,
        vm: iframeBox.left + targetBox.left + targetBox.width / 2 - popBox.width / 2,
        ve: iframeBox.left + targetBox.right - popMargins.right - popBox.width,
        hf: iframeBox.top + targetBox.top,
        hs: iframeBox.top + targetBox.top + popMargins.top,
        hm: iframeBox.top + targetBox.top + targetBox.height / 2 - popBox.height / 2,
        he: iframeBox.top + targetBox.bottom - popMargins.bottom - popBox.height,
    };

    function getPositioningData(d, v) {
        const [direction, variant] = reverseForRTL(DIRECTIONS[d], VARIANTS[v]);
        const result = { direction, variant };
        const vertical = ["t", "b", "c"].includes(d);
        const variantPrefix = vertical ? "v" : "h";
        const directionValue = directionsData[d];
        let variantValue = variantsData[variantPrefix + v];
        const [leftCompensation, topCompensation] = containerIsInIframe
            ? [iframeBox.left, iframeBox.top]
            : [0, 0];

        const [directionSize, variantSize] = vertical
            ? [popBox.height, popBox.width]
            : [popBox.width, popBox.height];
        let [directionMin, directionMax] = vertical
            ? [contBox.top + topCompensation, contBox.bottom + topCompensation]
            : [contBox.left + leftCompensation, contBox.right + leftCompensation];
        let [variantMin, variantMax] = vertical
            ? [contBox.left + leftCompensation, contBox.right + leftCompensation]
            : [contBox.top + topCompensation, contBox.bottom + topCompensation];

        if (containerIsHTMLNode) {
            if (vertical) {
                directionMin += container.scrollTop;
                directionMax += container.scrollTop;
            } else {
                variantMin += container.scrollTop;
                variantMax += container.scrollTop;
            }
        }

        // Compute overflows
        let directionOverflow = 0;
        if (Math.floor(directionValue) < Math.ceil(directionMin)) {
            directionOverflow = Math.floor(directionValue) - Math.ceil(directionMin);
        } else if (Math.ceil(directionValue + directionSize) > Math.floor(directionMax)) {
            directionOverflow =
                Math.ceil(directionValue + directionSize) - Math.floor(directionMax);
        }
        let variantOverflow = 0;
        if (Math.floor(variantValue) < Math.ceil(variantMin)) {
            variantOverflow = Math.floor(variantValue) - Math.ceil(variantMin);
        } else if (Math.ceil(variantValue + variantSize) > Math.floor(variantMax)) {
            variantOverflow = Math.ceil(variantValue + variantSize) - Math.floor(variantMax);
        }

        // All non zero values of variantOverflow lead to the
        // same malus value since it can be corrected by shifting
        let malus = Math.abs(directionOverflow) + (variantOverflow && 1);

        // Apply variant offset
        variantValue -= variantOverflow;
        result.variantOffset = -variantOverflow;

        const positioning = vertical
            ? { top: directionValue, left: variantValue }
            : { top: variantValue, left: directionValue };
        // Subtract the offsets of the containing block (relative to the
        // viewport). It can be done like that because the style top and
        // left were reset to 0px in `reposition`
        // https://developer.mozilla.org/en-US/docs/Web/CSS/Containing_block#identifying_the_containing_block
        result.top = positioning.top - popBox.top;
        result.left = positioning.left - popBox.left;
        if (d === "c") {
            // Artificial way to say the center direction is a fallback to every other
            // once there is a direction overflow since we can always shift the position
            // in any direction in that case
            malus = 1.001;
            result.top -= directionOverflow;
        } else if (shrink && malus) {
            const minTop = Math.floor(!vertical && v === "s" ? targetBox.top : contBox.top);
            result.top = Math.max(minTop, result.top);

            let height;
            if (vertical) {
                height = Math.abs(targetBox[direction] - (d === "t" ? directionMin : directionMax));
            } else {
                height = {
                    s: variantMax - targetBox.top,
                    m: variantMax - variantMin,
                    e: targetBox.bottom - variantMin,
                }[v];
            }
            result.maxHeight = Math.floor(height);
        }
        return { result, malus };
    }

    // Find best solution
    const matches = [];
    for (const d of directions) {
        for (const v of variants) {
            const match = getPositioningData(d, v);
            if (!match.malus) {
                // A perfect position match has been found.
                return match.result;
            }
            matches.push(match);
        }
        if (!flip) {
            // Stop when no flip is allowed
            break;
        }
    }
    // Settle for the first match with the least malus
    return matches.sort((a, b) => a.malus - b.malus)[0].result;
}

/**
 * Repositions the popper element relatively to the target element (according to options).
 * The positioning strategy is always a fixed positioning with top and left.
 *
 * The positioning solution is returned by the `computePosition` function.
 * It will get applied to the popper element and then returned for convenience.
 *
 * @param {HTMLElement} popper
 * @param {HTMLElement} target
 * @param {ComputePositionOptions} options
 * @returns {PositioningSolution} the applied positioning solution.
 */
export function reposition(popper, target, options) {
    // Reset popper style
    popper.style.position = "fixed";
    popper.style.top = "0px";
    popper.style.left = "0px";

    // Compute positioning solution
    const solution = computePosition(popper, target, { ...DEFAULTS, ...options });

    // Apply it
    const { top, left, maxHeight } = solution;
    popper.style.top = `${top}px`;
    popper.style.left = `${left}px`;
    if (maxHeight) {
        const existingMaxHeight = getComputedStyle(popper).maxHeight;
        popper.style.maxHeight =
            existingMaxHeight !== "none"
                ? `min(${existingMaxHeight}, ${maxHeight}px)`
                : `${maxHeight}px`;
    }

    return solution;
}
