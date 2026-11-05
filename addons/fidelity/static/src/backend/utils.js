import { useComponent, useState } from "@odoo/owl";
import { KeepLast } from "@web/core/utils/concurrency";

function useAsyncLockedMethod(method) {
    const component = useComponent();
    let called = false;
    return async (...args) => {
        if (called) {
            return;
        }
        try {
            called = true;
            return await method.call(component, ...args);
        } finally {
            called = false;
        }
    };
}

export function useTrackedAsync(asyncFn, options = {}) {
    /**
     * @type {{
     *  status: 'idle' | 'loading' | 'error' | 'success',
     * result: any,
     * lastArgs: any[]
     * }}
     */
    const state = useState({
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
