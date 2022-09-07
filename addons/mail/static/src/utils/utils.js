/** @odoo-module **/

import { delay } from 'web.concurrency';
import { unaccent } from 'web.utils';

//------------------------------------------------------------------------------
// Public
//------------------------------------------------------------------------------

const eventHandledWeakMap = new WeakMap();

/**
 * Returns the given string after cleaning it. The goal of the clean is to give
 * more convenient results when comparing it to potential search results, on
 * which the clean should also be called before comparing them.
 *
 * @param {string} searchTerm
 * @returns {string}
 */
function cleanSearchTerm(searchTerm) {
    return unaccent(searchTerm.toLowerCase());
}

/**
 * Returns whether the given event has been handled with the given markName.
 *
 * @param {Event} ev
 * @param {string} markName
 * @returns {boolean}
 */
function isEventHandled(ev, markName) {
    if (!eventHandledWeakMap.get(ev)) {
        return false;
    }
    return eventHandledWeakMap.get(ev).includes(markName);
}

/**
 * Marks the given event as handled by the given markName. Useful to allow
 * handlers in the propagation chain to make a decision based on what has
 * already been done.
 *
 * @param {Event} ev
 * @param {string} markName
 */
function markEventHandled(ev, markName) {
    if (!eventHandledWeakMap.get(ev)) {
        eventHandledWeakMap.set(ev, []);
    }
    eventHandledWeakMap.get(ev).push(markName);
}

/**
 * Wait a task tick, so that anything in micro-task queue that can be processed
 * is processed.
 */
async function nextTick() {
    await delay(0);
}

//------------------------------------------------------------------------------
// Export
//------------------------------------------------------------------------------

export {
    cleanSearchTerm,
    isEventHandled,
    markEventHandled,
    nextTick,
};
