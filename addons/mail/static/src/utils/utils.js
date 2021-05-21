/** @odoo-module **/

import { delay } from 'web.concurrency';
import { unaccent } from 'web.utils';

//------------------------------------------------------------------------------
// Public
//------------------------------------------------------------------------------

const classPatchMap = new WeakMap();
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
            await new Promise(resolve => setTimeout(resolve));
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

/**
 * Inspired by web.utils:patch utility function
 *
 * @param {Class} Class
 * @param {string} patchName
 * @param {Object} patch
 * @returns {function} unpatch function
 */
function patchClassMethods(Class, classPatch) {
    let metadata = classPatchMap.get(Class);
    if (!metadata) {
        metadata = {
            origMethods: new Map(),
            patches: new Set(),
        };
        classPatchMap.set(Class, metadata);
    }
    if (metadata.patches.has(classPatch)) {
        throw new Error(`Patch already exists.`);
    }
    metadata.patches.add(classPatch);
    applyPatch(Class, classPatch);

    function applyPatch(Class, patch) {
        Object.keys(patch).forEach(function (methodName) {
            const method = patch[methodName];
            if (typeof method === "function") {
                const original = Class[methodName];
                if (!(metadata.origMethods.has(methodName))) {
                    metadata.origMethods.set(methodName, original);
                }
                Class[methodName] = function (...args) {
                    const previousSuper = this._super;
                    this._super = original;
                    const res = method.call(this, ...args);
                    this._super = previousSuper;
                    return res;
                };
            }
        });
    }

    return () => unpatchClassMethods.bind(Class, classPatch);
}

/**
 * @param {Class} Class
 * @param {Object} instancePatch
 * @returns {function} unpatch function
 */
function patchInstanceMethods(Class, instancePatch) {
    return patchClassMethods(Class.prototype, instancePatch);
}

/**
 * Inspired by web.utils:unpatch utility function
 *
 * @param {Class} Class
 * @param {string} patchName
 */
function unpatchClassMethods(Class, classPatch) {
    const metadata = classPatchMap.get(Class);
    if (!metadata) {
        throw new Error(`Class was never patched.`);
    }
    if (!metadata.patches.has(classPatch)) {
        throw new Error(`Class was never patched with this patch.`);
    }
    // remove given patch
    metadata.patches.delete(classPatch);
    // reset to original
    for (const [methodName, method] in metadata.origMethods.entries()) {
        Class[methodName] = method;
    }
    // apply other patches
    for (const patch of metadata.patches) {
        patchClassMethods(Class, patch, metadata.patches[patch]);
    }
}

/**
 * @param {Class} Class
 * @param {string} instancePatch
 */
function unpatchInstanceMethods(Class, instancePatch) {
    return unpatchClassMethods(Class.prototype, instancePatch);
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
    patchClassMethods,
    patchInstanceMethods,
    unpatchClassMethods,
    unpatchInstanceMethods,
};
