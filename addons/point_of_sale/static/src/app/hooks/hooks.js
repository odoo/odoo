import { onMounted, onPatched, proxy, useListener } from "@odoo/owl";
import { ConnectionLostError } from "@web/core/network/rpc";
import { KeepLast } from "@web/core/utils/concurrency";
import { useRef } from "@web/owl2/utils";

/**
 * Assumes t-ref="root" in the root element of the component that uses this hook.
 */
export function useAutoFocusToLast() {
    const root = useRef("root");
    let target = null;
    function autofocus() {
        const prevTarget = target;
        const allInputs = root.el.querySelectorAll("input");
        target = allInputs[allInputs.length - 1];
        if (target && target !== prevTarget) {
            target.focus();
            target.selectionStart = target.selectionEnd = target.value.length;
        }
    }
    onMounted(autofocus);
    onPatched(autofocus);
}

export function useAsyncLockedMethod(method) {
    let called = false;
    return async (...args) => {
        if (called) {
            return;
        }
        try {
            called = true;
            return await method(...args);
        } finally {
            called = false;
        }
    };
}

/**
 * Wrapper for an async function that exposes the status of the function call.
 *
 * Sample use case:
 * ```js
 * {
 *   // inside in a component
 *   this.doPrint = useTrackedAsync(() => this.printOrderReceipt())
 *   this.doPrint.status === 'idle'
 *   this.doPrint.call() // triggers the given async function
 *   this.doPrint.status === 'loading'
 *   ['success', 'error].includes(this.doPrint.status) && this.doPrint.result
 * }
 * ```
 * @param {(...args: any[]) => Promise<any>} asyncFn
 * @param {{ keepLast?: boolean }} [options] - Options for managing concurrency.
 */
export function useTrackedAsync(asyncFn, options = {}) {
    /**
     * @type {{
     *  status: 'idle' | 'loading' | 'error' | 'success',
     * result: any,
     * lastArgs: any[]
     * }}
     */
    const state = proxy({
        status: "idle",
        result: null,
        lastArgs: null,
    });

    const { keepLast = false } = options;

    const baseMethod = async (...args) => {
        state.status = "loading";
        state.result = null;
        state.lastArgs = args;
        try {
            const result = await asyncFn(...args);
            state.status = "success";
            state.result = result;
        } catch (error) {
            state.status = "error";
            state.result = error;
            if (error instanceof ConnectionLostError) {
                throw error;
            }
        }
    };

    let call;
    if (keepLast) {
        const keepLastInstance = new KeepLast();
        call = (...args) => keepLastInstance.add(baseMethod(...args));
    } else {
        call = useAsyncLockedMethod(baseMethod);
    }

    return {
        get status() {
            return state.status;
        },
        get result() {
            return state.result;
        },
        get lastArgs() {
            return state.lastArgs;
        },
        call,
    };
}

export function useIsChildLarger(container) {
    const state = proxy({
        isLarger: false,
        maxItems: 0,
    });

    const computeSize = () => {
        if (!container.el || !container.el.children.length) {
            return;
        }

        let acc = 0;
        let nbrItems = 0;
        let isLarger = false;
        const containerWidth = container.el.clientWidth - 10;

        for (const child of container.el.children) {
            acc += child.clientWidth;
            if (acc < containerWidth) {
                nbrItems++;
            } else {
                isLarger = true;
                break;
            }
        }

        state.isLarger = isLarger;
        state.maxItems = nbrItems;
        if (state.isLarger) {
            state.maxItems = Math.max(0, state.maxItems - 1);
        }
    };

    useListener(window, "resize", () => {
        computeSize();
    });

    return {
        get isLarger() {
            return state.isLarger;
        },
        get maxItems() {
            return state.maxItems;
        },
        reload: () => {
            computeSize();
        },
    };
}
