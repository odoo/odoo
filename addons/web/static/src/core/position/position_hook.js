// @ts-check
/** @odoo-module native */

import {
    EventBus,
    onWillDestroy,
    useChildSubEnv,
    useEffect,
    useEnv,
    useRef,
} from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { reposition } from "@web/core/position/utils";
import { omit } from "@web/core/utils/collections/objects";
import { useThrottleForAnimation } from "@web/core/utils/timing";

/** @import { ComputePositionOptions, PositioningSolution } from "@web/core/position/utils" */

/**
 * @typedef {Object} UsePositionOptionsExtensionType
 * @property {(popperElement: HTMLElement, solution: PositioningSolution) => void} [onPositioned]
 * @typedef {ComputePositionOptions & UsePositionOptionsExtensionType} UsePositionOptions
 * @typedef PositioningControl
 * @property {() => void} lock
 * @property {() => void} unlock
 */

export const POSITION_BUS = Symbol("position-bus");

/**
 * @param {string} refName
 * @param {() => HTMLElement} getTarget
 * @param {UsePositionOptions} [options={}]
 * @returns {PositioningControl}
 */
export function usePosition(refName, getTarget, options = {}) {
    const ref = useRef(refName);
    let lock = false;
    /** @type {ComputePositionOptions["position"]} */
    let lastPosition;
    let lastRequestedPosition = options.position;
    const update = () => {
        const targetEl = getTarget();
        if (!ref.el || !targetEl?.isConnected || lock) {
            return false;
        }
        if (options.position !== lastRequestedPosition) {
            lastRequestedPosition = options.position;
            lastPosition = undefined;
        }
        const repositionOptions = omit(options, "onPositioned");
        if (lastPosition) {
            repositionOptions.position = lastPosition;
        }
        const solution = reposition(ref.el, targetEl, repositionOptions);
        lastPosition = /** @type {ComputePositionOptions["position"]} */ (
            `${solution.direction}-${solution.variant}`
        );
        options.onPositioned?.(ref.el, solution);
        return true;
    };

    const env = useEnv();
    const bus = /** @type {any} */ (env)[POSITION_BUS] || new EventBus();

    let executingUpdate = false;
    let updateRequested = false;
    const batchedUpdate = async () => {
        if (executingUpdate) {
            updateRequested = true;
            return;
        }
        executingUpdate = true;
        try {
            let positioned;
            do {
                // triggers arriving while a positioning runs are coalesced
                // into it; while a bail-out runs (on a bus shared with an
                // ancestor, the ancestor's trigger can reach this element
                // before it exists) they are retried, not dropped
                updateRequested = false;
                positioned = update();
                await Promise.resolve();
            } while (updateRequested && !positioned);
        } finally {
            executingUpdate = false;
        }
    };
    bus.addEventListener("update", batchedUpdate);
    onWillDestroy(() => bus.removeEventListener("update", batchedUpdate));

    const isTopmost = !(POSITION_BUS in env);
    if (isTopmost) {
        useChildSubEnv({ [POSITION_BUS]: bus });
    }

    useEffect(() => {
        bus.trigger("update");
    });

    if (isTopmost) {
        const throttledUpdate = useThrottleForAnimation(() => bus.trigger("update"));
        const scrollListener = (/** @type {Event} */ e) => {
            if (ref.el?.contains(/** @type {Node} */ (e.target))) {
                return;
            }
            throttledUpdate();
        };
        useEffect(
            (targetDocument) => {
                if (!targetDocument) {
                    return;
                }
                /** @type {Document[]} */
                const documents = [targetDocument];
                if (
                    targetDocument.defaultView?.top &&
                    targetDocument.defaultView.top !== targetDocument.defaultView
                ) {
                    try {
                        documents.push(targetDocument.defaultView.top.document);
                    } catch {}
                }
                for (const doc of documents) {
                    doc.addEventListener("scroll", scrollListener, { capture: true });
                    doc.addEventListener("load", throttledUpdate, { capture: true });
                }
                browser.addEventListener("resize", throttledUpdate);
                return () => {
                    for (const doc of documents) {
                        doc.removeEventListener("scroll", scrollListener, {
                            capture: true,
                        });
                        doc.removeEventListener("load", throttledUpdate, {
                            capture: true,
                        });
                    }
                    browser.removeEventListener("resize", throttledUpdate);
                };
            },
            () => [getTarget()?.ownerDocument],
        );
    }

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
