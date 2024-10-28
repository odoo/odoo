import { reposition } from "@web/core/position/utils";
import { omit } from "@web/core/utils/objects";
import { useThrottleForAnimation } from "@web/core/utils/timing";
import {
    EventBus,
    onWillDestroy,
    useChildSubEnv,
    useComponent,
    useEffect,
    useRef,
} from "@odoo/owl";

/**
 * @typedef {import("@web/core/position/utils").ComputePositionOptions} ComputePositionOptions
 * @typedef {import("@web/core/position/utils").PositioningSolution} PositioningSolution
 *
 * @typedef {Object} UsePositionOptionsExtensionType
 * @property {(popperElement: HTMLElement, solution: PositioningSolution) => void} [onPositioned]
 *  callback called when the positioning is done.
 * @typedef {ComputePositionOptions & UsePositionOptionsExtensionType} UsePositionOptions
 *
 * @typedef PositioningControl
 * @property {() => void} lock prevents further positioning updates
 * @property {() => void} unlock allows further positioning updates (triggers an update right away)
 */

/** @type {UsePositionOptions} */
const DEFAULTS = {
    margin: 0,
    position: "bottom",
};

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
 * @param {UsePositionOptions} [options={}] the options to be used for positioning
 * @returns {PositioningControl}
 *  control object to lock/unlock the positioning.
 */
export function usePosition(refName, getTarget, options = {}) {
    const ref = useRef(refName);
    let lock = false;
    const update = () => {
        const targetEl = getTarget();
        if (!ref.el || !targetEl?.isConnected || lock) {
            // No compute needed
            return;
        }
        const repositionOptions = { ...DEFAULTS, ...omit(options, "onPositioned") };
        const solution = reposition(ref.el, targetEl, repositionOptions);
        options.onPositioned?.(ref.el, solution);
    };

    const component = useComponent();
    const bus = component.env[POSITION_BUS] || new EventBus();

    let executingUpdate = false;
    const batchedUpdate = async () => {
        // not same as batch, here we're executing once and then awaiting
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
}
