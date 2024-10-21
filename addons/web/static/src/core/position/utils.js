import { localization } from "@web/core/l10n/localization";
import { omit } from "../utils/objects";

const { abs, ceil, floor } = Math;

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
 *  direction: Direction,
 *  variant: Variant,
 * }} PositioningSolution
 *
 * @typedef ComputePositionOptions
 * @property {HTMLElement | () => HTMLElement} [container] container element
 * @property {number} [margin=0]
 *  margin in pixels between the popper and the target.
 * @property {Direction | `${Direction}-${Variant}`} [position="bottom"]
 *  position of the popper relative to the target
 */

/** @type {{[d: string]: Direction}} */
const DIRECTIONS = { t: "top", r: "right", b: "bottom", l: "left" };
/** @type {{[v: string]: Variant}} */
const VARIANTS = { s: "start", m: "middle", e: "end", f: "fit" };
/** @type DirectionFlipOrder */
// const DIRECTION_FLIP_ORDER = { top: "tbrl", right: "rltb", bottom: "btrl", left: "lrbt" };
const DIRECTION_FLIP_ORDER = { top: "tb", right: "rl", bottom: "bt", left: "lr" };
/** @type VariantFlipOrder */
// const VARIANT_FLIP_ORDER = { start: "sme", middle: "mse", end: "ems", fit: "f" };
// const VARIANT_FLIP_ORDER = { start: "se", middle: "m", end: "es", fit: "f" };
const VARIANT_FLIP_ORDER = { start: "s", middle: "m", end: "e", fit: "f" };
/** @type DirectionFlipOrder */
const FIT_FLIP_ORDER = { top: "tb", right: "rl", bottom: "bt", left: "lr" };

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
function computePosition(popper, target, { container, margin, position }) {
    // Retrieve directions and variants
    let [direction, variant = "middle"] = position.split("-");
    if (localization.direction === "rtl") {
        if (["left", "right"].includes(direction)) {
            direction = direction === "left" ? "right" : "left";
        } else if (["start", "end"].includes(variant)) {
            // here direction is either "top" or "bottom"
            variant = variant === "start" ? "end" : "start";
        }
    }
    const directions =
        variant === "fit" ? FIT_FLIP_ORDER[direction] : DIRECTION_FLIP_ORDER[direction];
    const variants = VARIANT_FLIP_ORDER[variant];

    // Retrieve container
    if (!container) {
        container = popper.ownerDocument.documentElement;
    } else if (typeof container === "function") {
        container = container();
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

    // Compute positioning data
    const directionsData = {
        t: iframeBox.top + targetBox.top - popMargins.bottom - margin - popBox.height,
        b: iframeBox.top + targetBox.bottom + popMargins.top + margin,
        r: iframeBox.left + targetBox.right + popMargins.left + margin,
        l: iframeBox.left + targetBox.left - popMargins.right - margin - popBox.width,
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

    function getPositioningData(d = directions[0], v = variants[0], containerRestricted = false) {
        const result = { direction: DIRECTIONS[d], variant: VARIANTS[v] };
        const vertical = ["t", "b"].includes(d);
        const variantPrefix = vertical ? "v" : "h";
        const directionValue = directionsData[d];
        let variantValue = variantsData[variantPrefix + v];

        if (containerRestricted) {
            const [directionSize, variantSize] = vertical
                ? [popBox.height, popBox.width]
                : [popBox.width, popBox.height];
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

            // Compute overflow
            const directionOverflow =
                ceil(directionValue) < floor(directionMin) // negative overflow
                    ? ceil(directionValue) - floor(directionMin)
                    : floor(directionValue + directionSize) > ceil(directionMax) // positive overflow
                    ? floor(directionValue + directionSize) - ceil(directionMax)
                    : 0;
            const variantOverflow =
                ceil(variantValue) < floor(variantMin) // negative overflow
                    ? ceil(variantValue) - floor(variantMin)
                    : floor(variantValue + variantSize) > ceil(variantMax) // positive overflow
                    ? floor(variantValue + variantSize) - ceil(variantMax)
                    : 0;
            // All non zero values of variantOverflow lead to the same loss value since it can be
            // corrected by shifting
            result.loss = abs(directionOverflow) + (abs(variantOverflow) && 1);
            if (directionOverflow) {
                result.loss += 1_000_000;
            }
            // Shift the variant with overflow amount
            variantValue -= variantOverflow;
        }
        const positioning = vertical
            ? { top: directionValue, left: variantValue }
            : { top: variantValue, left: directionValue };
        // Subtract the offsets of the containing block (relative to the
        // viewport). It can be done like that because the style top and
        // left were reset to 0px in `reposition`
        // https://developer.mozilla.org/en-US/docs/Web/CSS/Containing_block#identifying_the_containing_block
        result.top = positioning.top - popBox.top;
        result.left = positioning.left - popBox.left;
        return result;
    }

    // Find best solution
    const matches = [];
    for (const d of directions) {
        for (const v of variants) {
            const match = getPositioningData(d, v, true);
            if (!match.loss) {
                // A perfect position match has been found.
                return match;
            }
            matches.push(match);
        }
    }
    // Settle for the first match with the least loss
    const bestMatch = matches.sort((a, b) => a.loss - b.loss)[0];
    return omit(bestMatch, "loss");
}

/**
 * avoir deux sets de solutions: une avec les el visibles et une avec les el qui débordent
 *
 * choix:
 * - dans les visibles, prendre celui dont la diff entre les deux bords (target et popper) est la plus petite
 * - dans les partiellement visibles, prendre celui dont la diff entre les deux bords (target et popper) est la plus petite également
 *
 * optimisation:
 * - on peut parfois détecter que l'une des directions est 1a éliminer
 */

/**
 * Ce qu'on devrait plutôt faire:
 * - calculer les shifts nécessaires dans les 4 directions (en ignorant les variants?)
 * - prendre le match où la différence entre le bord du popper et celui du target est minimale
 *
 * Peut-être aussi optimiser pour:
 * - ne pas prendre en compte les 3 variants, car ça revient probablement au même de check le shift
 *   sur un seul des variants ?
 * - s'arrêter si le shift rentre dans l'écran, car de toute façon on respecte le choix de la
 *   position souhaitée dans ce cas ?
 */

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
    const solution = computePosition(popper, target, options);

    // Apply it
    const { top, left, direction, variant } = solution;
    popper.style.top = `${top}px`;
    popper.style.left = `${left}px`;
    if (variant === "fit") {
        const styleProperty = ["top", "bottom"].includes(direction) ? "width" : "height";
        popper.style[styleProperty] = target.getBoundingClientRect()[styleProperty] + "px";
    }

    return solution;
}
