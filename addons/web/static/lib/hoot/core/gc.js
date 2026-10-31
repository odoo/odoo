/** @odoo-module */

import { getRunner } from "../main_runner";
import { logger } from "./logger";

/**
 * @typedef {{
 *  label: string;
 *  owner: string;
 *  ref: WeakRef<object>;
 * }} TrackedObject
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const { console, document, Map, performance, Set, WeakRef } = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * Tracking objects is only relevant when garbage collection can be forced, i.e.
 * when exposed by the browser (e.g. with the `--expose-gc` flag in Chrome).
 */
const canForceCollection = typeof globalThis.gc === "function";

/** @type {Set<TrackedObject>} */
let currentObjects = new Set();
/** @type {Set<TrackedObject>} */
let previousObjects = new Set();

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * Forces a major garbage collection, then logs the objects retained after the
 * job owning them (see {@link trackObject}) and the current heap size. It is meant
 * to be called right after a set of tests (e.g. a test file) has been executed.
 *
 * This is used for debugging memory leaks, or if the containing process running
 * unit tests doesn't know how much available memory it actually has.
 *
 * Does nothing if garbage collection cannot be forced: to enable this feature, the
 * containing process must simply use the `--expose-gc` flag.
 *
 * @param {string} label
 * @param {number} [testCount]
 */
export async function collectGarbageAndReport(label, testCount) {
    if (!canForceCollection) {
        return;
    }

    // Cleanup last retained textarea
    const textarea = document.createElement("textarea");
    document.body.appendChild(textarea);
    textarea.value = "aaa";
    textarea.focus();
    textarea.remove();

    // Run garbage collection: a "last resort" one also flushes the engine's own
    // caches (e.g. feedback of compiled code), which would otherwise retain some
    // objects well after their job, and report them as leaks
    await globalThis.gc({ type: "major", execution: "async", flavor: "last-resort" });

    // Log objects retained after the job owning them
    for (const [owner, labels] of getUncollectedObjects()) {
        console.log(`[MEMLEAK] ${label}: retained after "${owner}":`, labels.join(", "));
    }

    // Log memory usage
    const logs = [
        `[MEMINFO] ${label} (after GC)`,
        "- used:",
        performance.memory.usedJSHeapSize,
        "- total:",
        performance.memory.totalJSHeapSize,
        "- limit:",
        performance.memory.jsHeapSizeLimit,
    ];
    if (Number.isInteger(testCount)) {
        logs.push("- tests:", testCount);
    }
    console.log(...logs);
}

/**
 * Returns the labels of the objects tracked before the previous call which have
 * not been garbage collected yet, grouped by owner, and stops tracking them, so
 * that each one is only reported once.
 *
 * Objects tracked since the previous call are only checked on the next one, as
 * they may still be legitimately referenced by the latest jobs (e.g. the results
 * of the last test).
 *
 * Results are only relevant right after a major garbage collection.
 */
export function getUncollectedObjects() {
    /** @type {Map<string, string[]>} */
    const uncollected = new Map();
    for (const { label, owner, ref } of previousObjects) {
        if (ref.deref()) {
            if (!uncollected.has(owner)) {
                uncollected.set(owner, []);
            }
            uncollected.get(owner).push(label);
        }
    }
    previousObjects = currentObjects;
    currentObjects = new Set();
    return uncollected;
}

/**
 * Registers an object owned by the current job (test or suite):
 * - with the "debug" log level, it is logged to be inspected;
 * - otherwise, it is tracked to report it if it is not garbage collected some time
 *  after its job (see {@link getUncollectedObjects}).
 *
 * @param {string} label
 * @param {object} target
 */
export function trackObject(label, target) {
    if (logger.canLog("debug")) {
        logger.logDebug(label, target);
    } else if (canForceCollection) {
        const { suite, test } = getRunner().getCurrent();
        currentObjects.add({
            label,
            owner: (test || suite)?.fullName ?? "",
            ref: new WeakRef(target),
        });
    }
}
