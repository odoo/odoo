import { useChildSubEnv, useComponent, useLayoutEffect, useRef } from "@web/owl2/utils";
import { reposition } from "@web/core/position/utils";
import { omit } from "@web/core/utils/objects";
import { useThrottleForAnimation } from "@web/core/utils/timing";
import { EventBus, onWillDestroy } from "@odoo/owl";

/**
 * @typedef {import("@web/core/position/utils").ComputePositionOptions} ComputePositionOptions
 * @typedef {import("@web/core/position/utils").PositioningSolution} PositioningSolution
 *
 * @typedef {Object} UsePositionOptionsExtensionType
 * @property {(popperElement: HTMLElement, solution: PositioningSolution) => void} [onPositioned]
 *  callback called when the positioning is done.
 * @typedef {ComputePositionOptions & UsePositionOptionsExtensionType} UsePositionOptions
 * @property {boolean} [rememberPosition=true]
 *  keep the last position as the preferred one
 *
 * @typedef PositioningControl
 * @property {() => void} lock prevents further positioning updates
 * @property {() => void} unlock allows further positioning updates (triggers an update right away)
 */

export const POSITION_BUS = Symbol("position-bus");

/**
 * Makes sure that the `popper` element is always
 * placed at `position` from the `target` element.
 * If doing so the `popper` element is clipped off `container`,
 * sensible fallback positions are tried.
 * If all of fallback positions are also clipped off `container`,
 * the original position is used.
 *
 * Note: The popper element should be indicated in your template
 *       with a t-ref reference matching the refName argument, or bound
 *       to the provided signal via t-ref.
 *
 * @param {string | (() => HTMLElement)} popperRef
 *  Either the name of the reference to the popper element in the template
 *  (legacy Owl 2 ref-name string), or an Owl 3 signal returning the popper
 *  element. Both are supported during the Owl 2 -> 3 migration.
 * @param {() => HTMLElement} getTarget
 * @param {UsePositionOptions} [options={}] the options to be used for positioning
 * @returns {PositioningControl}
 *  control object to lock/unlock the positioning.
 */
export function usePosition(popperRef, getTarget, options = {}) {
    const rememberPosition = options.rememberPosition ?? true;
    // Transitional shim (Owl 2 -> 3): `popperRef` may be either a legacy
    // ref-name string (resolved through `useRef`) or an Owl 3 signal (a
    // function returning the element). Resolve "the current popper element"
    // once here so the rest of the hook is agnostic to which form was passed.
    // To remove once all callers pass a signal.
    let getPopperEl;
    if (typeof popperRef === "function") {
        // Owl 3 signal: calling it returns the current element.
        getPopperEl = popperRef;
    } else {
        // Legacy Owl 2 ref name: keep the original useRef(name).el behavior.
        const ref = useRef(popperRef);
        getPopperEl = () => ref.el;
    }
    let lock = false;
    const update = () => {
        const popperEl = getPopperEl();
        const targetEl = getTarget();
        if (!popperEl || !targetEl?.isConnected || lock) {
            // No compute needed
            return;
        }
        const repositionOptions = omit(options, "onPositioned");
        const solution = reposition(popperEl, targetEl, repositionOptions);
        // Don't memorize center position because it's a fallback that we don't want to keep if possible
        if (rememberPosition && solution.direction !== "center") {
            options.position = `${solution.direction}-${solution.variant}`; // memorize last position
        }
        options.onPositioned?.(popperEl, solution);
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
    useLayoutEffect(() => {
        // Reposition
        bus.trigger("update");

        if (isTopmost) {
            // Attach listeners to keep the positioning up to date
            const scrollListener = (e) => {
                if (getPopperEl()?.contains(e.target)) {
                    // In case the scroll event occurs inside the popper, do not reposition
                    return;
                }
                if (!e.target.contains(getTarget())) {
                    // the position target isn't inside the scrolled area, no need to reposition
                    return;
                }
                throttledUpdate();
            };
            // Get the ownerDocument of the target, and the topmost document
            // if the target is inside an iframe of same-origin
            // (c.f. html_builder), to handle scroll events at these 2 levels.
            const documents = [];
            const targetDocument = getTarget()?.ownerDocument;
            if (targetDocument) {
                documents.push(targetDocument);
                if (
                    targetDocument.defaultView &&
                    targetDocument.defaultView.top !== targetDocument.defaultView
                ) {
                    try {
                        documents.push(targetDocument.defaultView.top.document);
                    } catch {
                        // Don't access the top document if it is not allowed.
                        // (i.e. iframe origin or sandbox restriction)
                    }
                }
            }
            for (const document of documents) {
                document.addEventListener("scroll", scrollListener, { capture: true });
                document.addEventListener("load", throttledUpdate, { capture: true });
            }
            window.addEventListener("resize", throttledUpdate);
            return () => {
                for (const document of documents) {
                    document.removeEventListener("scroll", scrollListener, { capture: true });
                    document.removeEventListener("load", throttledUpdate, { capture: true });
                }
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
