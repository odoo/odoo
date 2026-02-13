import { BUTTON_HANDLER_SELECTOR, makeAsyncHandler, makeButtonHandler } from "./utils";

function setDeferredStatus(deferred) {
    deferred.status = "pending";
    deferred.promise.finally(() => {
        deferred.status = "done";
    });
}

export const globalInteractionsDeferred = Promise.withResolvers();
setDeferredStatus(globalInteractionsDeferred);
globalInteractionsDeferred.promise.then(stopWaitingForInteractions);

let interactionsDeferreds = [globalInteractionsDeferred];
export const registerInteractionDeferred = (deferred) => {
    setDeferredStatus(deferred);
    interactionsDeferreds.push(deferred);
};

/**
 * Using a map to register each element and each event type only once.
 * @type {Map<HTMLElement, Map<string, function>>}
 */
const bufferedEvents = new Map();
const nextBatch = [];

/**
 * Function to use as an event handler to replay the incoming event after the
 * interaction has been loaded. Note that blocking the incoming event is left
 * up to the caller (i.e. a potential wrapper, @see waitForInteractions ).
 *
 * @param {Event} ev
 * @returns {Promise}
 */
async function waitForInteractionAndRetrigger(ev) {
    const targetEl = ev.target;
    await Promise.race(interactionsDeferreds.map((def) => def.promise));
    // Once the base interactions have all been started, the buffer isn't needed
    // anymore and could even cause some bugs. Clearing all deferreds will make
    // sure to trigger events one last time as listeners should be attached by
    // now.
    if (globalInteractionsDeferred.status === "done") {
        interactionsDeferreds = [];
    }

    // At the end of the current execution queue, retrigger the event. Note that
    // the event is reconstructed: this is necessary in some cases, e.g. submit
    // buttons. Probably because the event was originally defaultPrevented.
    nextBatch.push((startedInteractions) => {
        if (
            // Extra safety check: the element might have been removed from the
            // DOM
            !targetEl.isConnected ||
            // Avoid clicking on a button outside of an open modal.
            (document.body.classList.contains("modal-open") && !targetEl.closest(".modal"))
        ) {
            removeBufferedEvent(targetEl, ev.type);
            return;
        }
        for (const def of startedInteractions) {
            if (!def.bufferedEvents || !def.bufferedEvents.length) {
                continue;
            }
            for (const [sel, eventType] of def.bufferedEvents) {
                if (ev.type === eventType && targetEl.matches(sel)) {
                    removeBufferedEvent(targetEl, ev.type);
                }
            }
        }
        // As we just removed the buffered events, handlers registered by
        // interactions will now be called directly. Other events retrigger
        // `waitForInteractionAndRetrigger`.
        targetEl.dispatchEvent(new ev.constructor(ev.type, ev));
    });
    planNextBatch();
}

let locked = false;

/**
 * After at least one interaction started, triggers the buffered events in batch
 * (at the end of the current execution queue).
 */
function planNextBatch() {
    if (locked) {
        return;
    }
    locked = true;
    setTimeout(() => {
        const startedInteractions = [];
        interactionsDeferreds = interactionsDeferreds.filter((def) => {
            if (def.status === "pending") {
                return true;
            }
            startedInteractions.push(def);
        });
        for (const cb of nextBatch) {
            cb(startedInteractions);
        }
        nextBatch.length = 0;
        locked = false;
    }, 0);
}

let waitingForInteractions = false;

// Note: blocking and retriggering only those specific event types is a
// limitation/a "risk".
export const loadingEffectEventTypes = [
    "pointerover",
    "pointerenter",
    "pointerdown",
    "pointerup",
    "click",
    "pointerout",
    "pointerleave",
];

/**
 * Automatically adds a loading effect on clicked buttons (that were not marked
 * with a specific class). Once an interaction is started, the events for
 * elements contained in that interaction's root will be triggered again. This
 * system is triggered as long as some base interactions (attached on elements
 * available on the page at load time) have yet to start.
 *
 * For forms, we automatically prevent submit events (since they can be
 * triggered without click on a button) but we do not retrigger them (as it
 * could duplicate the re-trigger of a click on a submit button otherwise).
 * However, submitting a form in any way should most of the time simulate a
 * click on the submit button if any anyway.
 *
 * @see stopWaitingForInteractions
 */
function waitForInteractions() {
    if (globalInteractionsDeferred.status !== "pending" || waitingForInteractions) {
        return;
    }
    waitingForInteractions = true;
    document.body.classList.add("o_interactions_js_waiting");

    const mainEl = document.getElementById("wrapwrap") || document.body;
    const loadingEffectButtonEls = [...mainEl.querySelectorAll(BUTTON_HANDLER_SELECTOR)]
        // We target all buttons but...
        .filter(
            (el) =>
                // ... we allow to disable the effect by adding a specific class
                // if needed.
                !el.classList.contains("o_no_wait_interactions_js") &&
                // ... we also allow not to consider links with a href different
                // from "#". They could be linked to handlers that prevent their
                // default behavior but we consider that following the link
                // should still be relevant in that case.
                !(el.nodeName === "A" && el.href && el.getAttribute("href") !== "#")
        );
    for (const buttonEl of loadingEffectButtonEls) {
        for (const eventType of loadingEffectEventTypes) {
            const loadingEffectHandler =
                eventType === "click"
                    ? makeButtonHandler(waitForInteractionAndRetrigger, true, true, true)
                    : makeAsyncHandler(waitForInteractionAndRetrigger, true, true, true);
            registerBufferedEventsHandler(buttonEl, eventType, loadingEffectHandler);
        }
    }

    for (const formEl of document.querySelectorAll("form:not(.o_no_wait_interactions_js)")) {
        registerBufferedEventsHandler(formEl, "submit", (ev) => {
            ev.preventDefault();
            ev.stopImmediatePropagation();
        });
    }
}
/**
 * Undo what @see waitForInteractions did.
 */
function stopWaitingForInteractions() {
    if (!waitingForInteractions) {
        return;
    }
    waitingForInteractions = false;
    document.body.classList.remove("o_interactions_js_waiting");

    for (const [el, events] of bufferedEvents) {
        for (const [type, handler] of events) {
            el.removeEventListener(type, handler, { capture: true });
        }
        bufferedEvents.delete(el);
    }
}
/**
 * Adds the given event listener and saves it for later removal.
 *
 * @param {HTMLElement} el
 * @param {string} type
 * @param {Function} handler
 */
function registerBufferedEventsHandler(el, type, handler) {
    el.addEventListener(type, handler, { capture: true });
    const eventHandlerMap = bufferedEvents.get(el) || bufferedEvents.set(el, new Map()).get(el);
    if (!eventHandlerMap.has(type)) {
        eventHandlerMap.set(type, handler);
    }
}
/**
 * Removes the event listener attached to the given element and event type.
 *
 * @param {HTMLElement} el
 * @param {string} type
 */
function removeBufferedEvent(el, type) {
    const events = bufferedEvents.get(el);
    if (!events || !events.has(type)) {
        return;
    }
    el.removeEventListener(type, events.get(type), { capture: true });
    events.delete(type);
    if (!events.size) {
        bufferedEvents.delete(el);
    }
}

// Start waiting for lazy loading as soon as the DOM is available
if (document.readyState !== "loading") {
    waitForInteractions();
} else {
    document.addEventListener("DOMContentLoaded", function () {
        waitForInteractions();
    });
}
