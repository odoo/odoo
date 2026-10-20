import { addLoadingEffect } from "@web/core/utils/loading_effect";

export const DEBOUNCE = 400;
export const BUTTON_HANDLER_SELECTOR =
    'a, button, input[type="submit"], input[type="button"], .btn';

/**
 * Protects a function which is to be used as a handler by preventing its
 * execution for the duration of a previous call to it (including async
 * parts of that call).
 *
 * @param {function} fct
 *      The function which is to be used as a handler. If a promise
 *      is returned, it is used to determine when the handler's action is
 *      finished. Otherwise, the return is used as jQuery uses it.
 * @param {boolean} preventEventPropagation
 *      set to true if the handler should prevent event propagation
 */
export function makeAsyncHandler(fct, preventEventPropagation = false) {
    let pending = false;
    function _isLocked() {
        return pending;
    }
    function _lock() {
        pending = true;
    }
    function _unlock() {
        pending = false;
    }
    return function (ev) {
        if (preventEventPropagation) {
            ev.preventDefault();
            ev.stopPropagation();
            ev.stopImmediatePropagation();
        }
        if (_isLocked()) {
            // If a previous call to this handler is still pending, ignore
            // the new call.
            return;
        }

        _lock();
        const result = fct.apply(this, arguments);
        Promise.resolve(result).finally(_unlock);
        return result;
    };
}

/**
 * Creates a debounced version of a function to be used as a button click
 * handler. Also improves the handler to disable the button for the time of
 * the debounce and/or the time of the async actions it performs.
 *
 * Limitation: if two handlers are put on the same button, the button will
 * become enabled again once any handler's action finishes (multiple click
 * handlers should however not be bound to the same button).
 *
 * @param {function} fct
 *      The function which is to be used as a button click handler. If a
 *      promise is returned, it is used to determine when the button can be
 *      re-enabled. Otherwise, the return is used as jQuery uses it.
 * @param {boolean} preventEventPropagation
 *      set to true if the handler should prevent event propagation
 */
export function makeButtonHandler(fct, preventEventPropagation = false) {
    // Fallback: if the final handler is not bound to a button, at least
    // make it an async handler (also handles the case where some events
    // might ignore the disabled state of the button).
    fct = makeAsyncHandler(fct, preventEventPropagation);

    return function (ev) {
        const handlerResult = fct.apply(this, arguments);

        const buttonEl = ev.target.closest(BUTTON_HANDLER_SELECTOR);
        if (!(buttonEl instanceof HTMLElement)) {
            return handlerResult;
        }

        // Disable the button for the duration of the handler's action
        // or at least for the duration of the click debounce. This makes
        // a 'real' debounce creation useless. Also, during the debouncing
        // part, the button is disabled without any visual effect.
        buttonEl.classList.add("pe-none");
        let showDebouncedLoading = false;
        const addLoadingIfPending = () => {
            buttonEl.classList.remove("pe-none");
            if (showDebouncedLoading) {
                const restore = addLoadingEffect(buttonEl);
                Promise.resolve(handlerResult).then(restore, restore);
            }
        };
        Promise.race([
            handlerResult,
            new Promise((resolve) => setTimeout(resolve, DEBOUNCE)).then(() => {
                showDebouncedLoading = true;
            }),
        ]).then(addLoadingIfPending, addLoadingIfPending);

        return handlerResult;
    };
}
