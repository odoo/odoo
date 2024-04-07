/** @odoo-module **/

import {
    BUTTON_HANDLER_SELECTOR,
    makeAsyncHandler,
    makeButtonHandler,
} from '@web/legacy/js/core/minimal_dom';

// Track when all JS files have been lazy loaded. Will allow to unblock the
// related DOM sections when the whole JS have been loaded and executed.
let allScriptsLoadedResolve = null;
const _allScriptsLoaded = new Promise(resolve => {
    allScriptsLoadedResolve = resolve;
}).then(stopWaitingLazy);

const retriggeringWaitingProms = [];
/**
 * Function to use as an event handler to replay the incoming event after the
 * whole lazy JS has been loaded. Note that blocking the incoming event is left
 * up to the caller (i.e. a potential wrapper, @see waitLazy).
 *
 * @param {Event} ev
 * @returns {Promise}
 */
async function waitForLazyAndRetrigger(ev) {
    // Wait for the lazy JS to be loaded before re-triggering the event.
    const targetEl = ev.target;
    await _allScriptsLoaded;
    // Loaded scripts were able to add a delay to wait for before re-triggering
    // events: we wait for it here.
    await Promise.all(retriggeringWaitingProms);

    // At the end of the current execution queue, retrigger the event. Note that
    // the event is reconstructed: this is necessary in some cases, e.g. submit
    // buttons. Probably because the event was originally defaultPrevented.
    setTimeout(() => {
        // Extra safety check: the element might have been removed from the DOM
        if (targetEl.isConnected) {
            targetEl.dispatchEvent(new ev.constructor(ev.type, ev));
        }
    }, 0);
}

const loadingEffectHandlers = [];
/**
 * Adds the given event listener and saves it for later removal.
 *
 * @param {HTMLElement} el
 * @param {string} type
 * @param {Function} handler
 */
function registerLoadingEffectHandler(el, type, handler) {
    el.addEventListener(type, handler, {capture: true});
    loadingEffectHandlers.push({el, type, handler});
}

let waitingLazy = false;

/**
 * Automatically adds a loading effect on clicked buttons (that were not marked
 * with a specific class). Once the whole JS has been loaded, the events will be
 * triggered again.
 *
 * For forms, we automatically prevent submit events (since can be triggered
 * without click on a button) but we do not retrigger them (could be duplicate
 * with re-trigger of a click on a submit button otherwise). However, submitting
 * a form in any way should most of the time simulate a click on the submit
 * button if any anyway.
 *
 * @todo This function used to consider the o_wait_lazy_js class. In master, the
 * uses of this classes should be removed in XML templates.
 * @see stopWaitingLazy
 */
function waitLazy() {
    if (waitingLazy) {
        return;
    }
    waitingLazy = true;

    document.body.classList.add('o_lazy_js_waiting');

    // TODO should probably find the wrapwrap another way but in future versions
    // the element will be gone anyway.
    const mainEl = document.getElementById('wrapwrap') || document.body;
    const loadingEffectButtonEls = [...mainEl.querySelectorAll(BUTTON_HANDLER_SELECTOR)]
        // We target all buttons but...
        .filter(el => {
            // ... we allow to disable the effect by adding a specific class if
            // needed. Note that if some non-lazy loaded code is adding an event
            // handler on some buttons, it means that if they do not have that
            // class, they will show a loading effect and not do anything until
            // lazy JS is loaded anyway. This is not ideal, especially since
            // this was added as a stable fix/imp, but this is a compromise: on
            // next page visits, the cache should limit to effect of the lazy
            // loading anyway.
            return !el.classList.contains('o_no_wait_lazy_js')
                // ... we also allow do not consider links with a href which is
                // not "#". They could be linked to handlers that prevent their
                // default behavior but we consider that following the link
                // should still be relevant in that case.
                && !(el.nodeName === 'A' && el.href && el.getAttribute('href') !== '#');
        });
    // Note: this is a limitation/a "risk" to only block and retrigger those
    // specific event types.
    const loadingEffectEventTypes = ['mouseover', 'mouseenter', 'mousedown', 'mouseup', 'click', 'mouseout', 'mouseleave'];
    for (const buttonEl of loadingEffectButtonEls) {
        for (const eventType of loadingEffectEventTypes) {
            const loadingEffectHandler = eventType === 'click'
                ? makeButtonHandler.call({
                    '__makeButtonHandler_preventDefault': true,
                    '__makeButtonHandler_stopImmediatePropagation': true,
                }, waitForLazyAndRetrigger)
                : makeAsyncHandler.call({
                    '__makeAsyncHandler_stopImmediatePropagation': true,
                }, waitForLazyAndRetrigger, true);
            registerLoadingEffectHandler(buttonEl, eventType, loadingEffectHandler);
        }
    }

    for (const formEl of document.querySelectorAll('form:not(.o_no_wait_lazy_js)')) {
        registerLoadingEffectHandler(formEl, 'submit', ev => {
            ev.preventDefault();
            ev.stopImmediatePropagation();
        });
    }
}
/**
 * Undo what @see waitLazy did.
 */
function stopWaitingLazy() {
    if (!waitingLazy) {
        return;
    }
    waitingLazy = false;

    document.body.classList.remove('o_lazy_js_waiting');

    for (const { el, type, handler } of loadingEffectHandlers) {
        el.removeEventListener(type, handler, {capture: true});
    }
}

// Start waiting for lazy loading as soon as the DOM is available
if (document.readyState !== 'loading') {
    waitLazy();
} else {
    document.addEventListener('DOMContentLoaded', function () {
        waitLazy();
    });
}

// As soon as the document is fully loaded, start loading the whole remaining JS
if (document.readyState === 'complete') {
    setTimeout(_loadScripts, 0);
} else {
    window.addEventListener('load', function () {
        setTimeout(_loadScripts, 0);
    });
}

/**
 * @param {DOMElement[]} scripts
 * @param {integer} index
 */
function _loadScripts(scripts, index) {
    if (scripts === undefined) {
        scripts = document.querySelectorAll('script[data-src]');
    }
    if (index === undefined) {
        index = 0;
    }
    if (index >= scripts.length) {
        allScriptsLoadedResolve();
        return;
    }
    const script = scripts[index];
    script.addEventListener('load', _loadScripts.bind(this, scripts, index + 1));
    script.setAttribute('defer', 'defer');
    script.src = script.dataset.src;
    script.removeAttribute('data-src');
}

export default {
    loadScripts: _loadScripts,
    allScriptsLoaded: _allScriptsLoaded,
    registerPageReadinessDelay: retriggeringWaitingProms.push.bind(retriggeringWaitingProms),
};
