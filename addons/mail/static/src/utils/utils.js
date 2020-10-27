odoo.define('mail/static/src/utils/utils.js', function (require) {
'use strict';

const { delay } = require('web.concurrency');
const {
    patch: webUtilsPatch,
    unpatch: webUtilsUnpatch,
} = require('web.utils');

//------------------------------------------------------------------------------
// Public
//------------------------------------------------------------------------------

const classPatchMap = new WeakMap();
const eventHandledWeakMap = new WeakMap();

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
function patchClassMethods(Class, patchName, patch) {
    let metadata = classPatchMap.get(Class);
    if (!metadata) {
        metadata = {
            origMethods: {},
            patches: {},
            current: []
        };
        classPatchMap.set(Class, metadata);
    }
    if (metadata.patches[patchName]) {
        throw new Error(`Patch [${patchName}] already exists`);
    }
    metadata.patches[patchName] = patch;
    applyPatch(Class, patch);
    metadata.current.push(patchName);

    function applyPatch(Class, patch) {
        Object.keys(patch).forEach(function (methodName) {
            const method = patch[methodName];
            if (typeof method === "function") {
                const original = Class[methodName];
                if (!(methodName in metadata.origMethods)) {
                    metadata.origMethods[methodName] = original;
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

    return () => unpatchClassMethods.bind(Class, patchName);
}

/**
 * @param {Class} Class
 * @param {string} patchName
 * @param {Object} patch
 * @returns {function} unpatch function
 */
function patchInstanceMethods(Class, patchName, patch) {
    return webUtilsPatch(Class, patchName, patch);
}

/**
 * Inspired by web.utils:unpatch utility function
 *
 * @param {Class} Class
 * @param {string} patchName
 */
function unpatchClassMethods(Class, patchName) {
    let metadata = classPatchMap.get(Class);
    if (!metadata) {
        return;
    }
    classPatchMap.delete(Class);

    // reset to original
    for (let k in metadata.origMethods) {
        Class[k] = metadata.origMethods[k];
    }

    // apply other patches
    for (let name of metadata.current) {
        if (name !== patchName) {
            patchClassMethods(Class, name, metadata.patches[name]);
        }
    }
}

/**
 * @param {Class} Class
 * @param {string} patchName
 */
function unpatchInstanceMethods(Class, patchName) {
    return webUtilsUnpatch(Class, patchName);
}

//------------------------------------------------------------------------------
// Export
//------------------------------------------------------------------------------

return {
    executeGracefully,
    isEventHandled,
    markEventHandled,
    nextTick,
    patchClassMethods,
    patchInstanceMethods,
    unpatchClassMethods,
    unpatchInstanceMethods,
};

});
