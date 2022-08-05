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
 * Executes the provided functions in order, but with a potential delay between
 * them if they take too much time. This is done in order to avoid blocking the
 * main thread for too long.
 *
 * @param {function[]} functions
 * @param {integer} [maxTimeFrame=100] time (in ms) until a delay is introduced
 */
async function executeGracefully(functions, maxTimeFrame = 100) {
    let startDate = new Date();
    for (const func of functions) {
        if (new Date() - startDate > maxTimeFrame) {
            await new Promise(resolve => setTimeout(resolve, 50));
            startDate = new Date();
        }
        await func();
    }
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
    executeGracefully,
    isEventHandled,
    markEventHandled,
    nextTick,
};
