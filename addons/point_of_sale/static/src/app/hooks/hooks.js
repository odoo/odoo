import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog, AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ErrorDialog } from "@web/core/errors/error_dialogs";
import {
    useEnv,
    onMounted,
    onPatched,
    useComponent,
    useRef,
    useState,
    useExternalListener,
} from "@odoo/owl";
import { KeepLast } from "@web/core/utils/concurrency";

/**
 * Introduce error handlers in the component.
 *
 * IMPROVEMENT: This is a terrible hook. There could be a better way to handle
 * the error when the order failed to sync.
 * FIXME POSREF: move this to the error_handler registry.
 */
export function useErrorHandlers() {
    const component = useComponent();
    const dialog = useEnv().services.dialog;

    component._handlePushOrderError = async function (error) {
        // This error handler receives `error` equivalent to `error.message` of the rpc error.
        if (error.message === "Backend Invoice") {
            dialog.add(ConfirmationDialog, {
                title: _t("Please print the invoice from the backend"),
                body:
                    _t(
                        "The order has been synchronized earlier. Please make the invoice from the backend for the order: "
                    ) + error.data.order.name,
            });
        } else if (error.code < 0) {
            // XmlHttpRequest Errors
            dialog.add(ConfirmationDialog, {
                title: _t("Unable to sync order"),
                body: _t(
                    "Check the internet connection then try to sync again by clicking on the red wifi button (upper right of the screen)."
                ),
            });
        } else if (error.data) {
            // OpenERP Server Errors
            dialog.add(ErrorDialog, {
                traceback:
                    error.data.debug.status.message_body ||
                    _t("The server encountered an error while receiving your order."),
            });
        } else {
            // ???
            await dialog.add(AlertDialog, {
                title: _t("Unknown Error"),
                body: _t("The order could not be sent to the server due to an unknown error"),
                showReloadButton: true,
            });
        }
    };
}

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

/**
 * Wrapper for an async function that exposes the status of the function call.
 *
 * Sample use case:
 * ```js
 * {
 *   // inside in a component
 *   this.doPrint = useTrackedAsync(() => this.printReceipt())
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

export function useIsChildLarger(container) {
    const state = useState({
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
        const oldLargerState = state.isLarger;
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
        if (!oldLargerState && state.isLarger) {
            state.maxItems--;
        }
    };

    useExternalListener(window, "resize", () => {
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
