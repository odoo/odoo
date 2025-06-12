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
const DIRECTION_FLIP_ORDER = { top: "tbrl", right: "rltb", bottom: "btrl", left: "lrbt" };
/** @type VariantFlipOrder */
const VARIANT_FLIP_ORDER = { start: "sme", middle: "mse", end: "ems", fit: "f" };
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
        const vertical = ["t", "b"].includes(d);
        const variantPrefix = vertical ? "v" : "h";
        const directionValue = directionsData[d];
        const variantValue = variantsData[variantPrefix + v];

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
            ? { top: directionValue, left: variantValue }
            : { top: variantValue, left: directionValue };
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

<<<<<<< 54204e664ed1924f512ba4626be010e39c2d17a3:addons/web/static/src/core/position/utils.js
    return solution;
||||||| 4a603c6314316716913b0c4de71affec075e15ea:addons/web/static/src/core/position_hook.js
    options.onPositioned?.(popper, position);
}

const POSITION_BUS = Symbol("position-bus");

/**
 * Makes sure that the `popper` element is always
 * placed at `position` from the `target` element.
 * If doing so the `popper` element is clipped off `container`,
 * sensible fallback positions are tried.
 * If all of fallback positions are also clipped off `container`,
 * the original position is used.
 *
 * Note: The popper element should be indicated in your template
 *       with a t-ref reference matching the refName argument.
 *
 * @param {string} refName
 *  name of the reference to the popper element in the template.
 * @param {() => HTMLElement} getTarget
 * @param {Options} [options={}] the options to be used for positioning
 * @returns {PositioningControl}
 *  control object to lock/unlock the positioning.
 */
export function usePosition(refName, getTarget, options = {}) {
    const ref = useRef(refName);
    let lock = false;
    const update = () => {
        const targetEl = getTarget();
        if (!ref.el || !targetEl || lock) {
            // No compute needed
            return;
        }

        // Prepare
        const iframe = getIFrame(ref.el, targetEl);
        reposition(ref.el, targetEl, { ...DEFAULTS, ...options }, iframe);
    };

    const component = useComponent();
    const bus = component.env[POSITION_BUS] || new EventBus();

    let executingUpdate = false;
    const batchedUpdate = async () => {
        if (!executingUpdate) {
            executingUpdate = true;
            update();
            await Promise.resolve();
            executingUpdate = false;
        }
    };
    bus.addEventListener("update", batchedUpdate);
    onWillDestroy(() => bus.removeEventListener("update", batchedUpdate));

    const isTopmost = !(POSITION_BUS in component.env);
    if (isTopmost) {
        useChildSubEnv({ [POSITION_BUS]: bus });
    }

    const throttledUpdate = useThrottleForAnimation(() => bus.trigger("update"));
    useEffect(() => {
        // Reposition
        bus.trigger("update");

        if (isTopmost) {
            // Attach listeners to keep the positioning up to date
            const scrollListener = (e) => {
                if (ref.el?.contains(e.target)) {
                    // In case the scroll event occurs inside the popper, do not reposition
                    return;
                }
                throttledUpdate();
            };
            const targetDocument = getTarget()?.ownerDocument;
            targetDocument?.addEventListener("scroll", scrollListener, { capture: true });
            targetDocument?.addEventListener("load", throttledUpdate, { capture: true });
            window.addEventListener("resize", throttledUpdate);
            return () => {
                targetDocument?.removeEventListener("scroll", scrollListener, { capture: true });
                targetDocument?.removeEventListener("load", throttledUpdate, { capture: true });
                window.removeEventListener("resize", throttledUpdate);
            };
        }
    });

    return {
        lock: () => {
            lock = true;
        },
        unlock: () => {
            lock = false;
            bus.trigger("update");
        },
    };
=======
    options.onPositioned?.(popper, position);
}

const POSITION_BUS = Symbol("position-bus");

/**
 * Makes sure that the `popper` element is always
 * placed at `position` from the `target` element.
 * If doing so the `popper` element is clipped off `container`,
 * sensible fallback positions are tried.
 * If all of fallback positions are also clipped off `container`,
 * the original position is used.
 *
 * Note: The popper element should be indicated in your template
 *       with a t-ref reference matching the refName argument.
 *
 * @param {string} refName
 *  name of the reference to the popper element in the template.
 * @param {() => HTMLElement} getTarget
 * @param {Options} [options={}] the options to be used for positioning
 * @returns {PositioningControl}
 *  control object to lock/unlock the positioning.
 */
export function usePosition(refName, getTarget, options = {}) {
    const ref = useRef(refName);
    let lock = false;
    const update = () => {
        const targetEl = getTarget();
        if (!ref.el || !targetEl || lock) {
            // No compute needed
            return;
        }

        // Prepare
        const iframe = getIFrame(ref.el, targetEl);
        reposition(ref.el, targetEl, { ...DEFAULTS, ...options }, iframe);
    };

    const component = useComponent();
    const bus = component.env[POSITION_BUS] || new EventBus();

    let executingUpdate = false;
    const batchedUpdate = async () => {
        if (!executingUpdate && ref.el) {
            executingUpdate = true;
            update();
            await Promise.resolve();
            executingUpdate = false;
        }
    };
    bus.addEventListener("update", batchedUpdate);
    onWillDestroy(() => bus.removeEventListener("update", batchedUpdate));

    const isTopmost = !(POSITION_BUS in component.env);
    if (isTopmost) {
        useChildSubEnv({ [POSITION_BUS]: bus });
    }

    const throttledUpdate = useThrottleForAnimation(() => bus.trigger("update"));
    useEffect(() => {
        // Reposition
        bus.trigger("update");

        if (isTopmost) {
            // Attach listeners to keep the positioning up to date
            const scrollListener = (e) => {
                if (ref.el?.contains(e.target)) {
                    // In case the scroll event occurs inside the popper, do not reposition
                    return;
                }
                throttledUpdate();
            };
            const targetDocument = getTarget()?.ownerDocument;
            targetDocument?.addEventListener("scroll", scrollListener, { capture: true });
            targetDocument?.addEventListener("load", throttledUpdate, { capture: true });
            window.addEventListener("resize", throttledUpdate);
            return () => {
                targetDocument?.removeEventListener("scroll", scrollListener, { capture: true });
                targetDocument?.removeEventListener("load", throttledUpdate, { capture: true });
                window.removeEventListener("resize", throttledUpdate);
            };
        }
    });

    return {
        lock: () => {
            lock = true;
        },
        unlock: () => {
            lock = false;
            bus.trigger("update");
        },
    };
>>>>>>> 21dd250181da4a208f24ebfbe19a789c67343131:addons/web/static/src/core/position_hook.js
}
