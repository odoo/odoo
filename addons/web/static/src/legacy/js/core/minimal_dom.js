/** @odoo-module **/

export const DEBOUNCE = 400;
export const BUTTON_HANDLER_SELECTOR = 'a, button, input[type="submit"], input[type="button"], .btn';

/**
 * Protects a function which is to be used as a handler by preventing its
 * execution for the duration of a previous call to it (including async
 * parts of that call).
 *
 * Limitation: as the handler is ignored during async actions,
 * the 'preventDefault' or 'stopPropagation' calls it may want to do
 * will be ignored too. Using the 'preventDefault' and 'stopPropagation'
 * arguments solves that problem.
 *
 * @param {function} fct
 *      The function which is to be used as a handler. If a promise
 *      is returned, it is used to determine when the handler's action is
 *      finished. Otherwise, the return is used as jQuery uses it.
 * @param {function|boolean} preventDefault
 * @param {function|boolean} stopPropagation
 */
export function makeAsyncHandler(fct, preventDefault, stopPropagation) {
    // TODO in master, add those as arguments.
    const stopImmediatePropagation = this && this.__makeAsyncHandler_stopImmediatePropagation;

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
        if (preventDefault === true || preventDefault && preventDefault()) {
            ev.preventDefault();
        }
        if (stopPropagation === true || stopPropagation && stopPropagation()) {
            ev.stopPropagation();
        }
        if (stopImmediatePropagation === true || stopImmediatePropagation && stopImmediatePropagation()) {
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
 */
export function makeButtonHandler(fct) {
    // TODO in master, add those as arguments. Even though buttons are probably
    // blocked by the o_website_btn_loading and related classes, it is not
    // necessarily true for all event types.
    const preventDefault = this && this.__makeButtonHandler_preventDefault;
    const stopPropagation = this && this.__makeButtonHandler_stopPropagation;
    const stopImmediatePropagation = this && this.__makeButtonHandler_stopImmediatePropagation;

    // Fallback: if the final handler is not bound to a button, at least
    // make it an async handler (also handles the case where some events
    // might ignore the disabled state of the button).
    fct = makeAsyncHandler.call({
        '__makeAsyncHandler_stopImmediatePropagation': stopImmediatePropagation,
    }, fct, preventDefault, stopPropagation);

    return function (ev) {
        const result = fct.apply(this, arguments);

        const buttonEl = ev.target && ev.target.closest && ev.target.closest(BUTTON_HANDLER_SELECTOR);
        if (!(buttonEl instanceof HTMLElement)) {
            return result;
        }

        // Disable the button for the duration of the handler's action
        // or at least for the duration of the click debounce. This makes
        // a 'real' debounce creation useless. Also, during the debouncing
        // part, the button is disabled without any visual effect.
        buttonEl.classList.add('pe-none');
        Promise.resolve(DEBOUNCE && new Promise(r => setTimeout(r, DEBOUNCE)))
            .then(function () {
                buttonEl.classList.remove('pe-none');
                const restore = addButtonLoadingEffect(buttonEl);
                return Promise.resolve(result).finally(restore);
            });

        return result;
    };
}

/**
 * Gives the button a loading effect by disabling it and adding a `fa`
 * spinner icon.
 * The existing button `fa` icons will be hidden through css.
 *
 * @param {HTMLElement} btnEl - the button to disable/load
 * @return {function} a callback function that will restore the button
 *         initial state
 */
export function addButtonLoadingEffect(btnEl) {
    if (!(btnEl instanceof HTMLElement)) {
        return () => {};
    }
    // Note that pe-none is used alongside "disabled" so that the behavior is
    // the same on links not using the "btn" class -> pointer-events disabled.
    btnEl.classList.add('o_website_btn_loading', 'disabled', 'pe-none');
    btnEl.disabled = true;
    const loaderEl = document.createElement('span');
    loaderEl.classList.add('fa', 'fa-refresh', 'fa-spin', 'me-2');
    btnEl.prepend(loaderEl);
    return () => {
        btnEl.classList.remove('o_website_btn_loading', 'disabled', 'pe-none');
        btnEl.disabled = false;
        loaderEl.remove();
    };
}
