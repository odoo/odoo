// @ts-check
/** @odoo-module native */

/** @type {(() => void)[]} */
let reads = [];
/** @type {(() => void)[]} */
let writes = [];
let scheduled = false;
let flushing = false;

function flush() {
    scheduled = false;
    flushing = true;
    /** @type {unknown[]} */
    const errors = [];
    try {
        while (reads.length || writes.length) {
            const batch = reads;
            reads = [];
            for (const fn of batch) {
                run(fn, errors);
            }
            const pending = writes;
            writes = [];
            for (const fn of pending) {
                run(fn, errors);
            }
        }
    } finally {
        flushing = false;
    }
    if (errors.length) {
        throw errors.length === 1 ? errors[0] : new AggregateError(errors);
    }
}

/**
 * @param {() => void} fn
 * @param {unknown[]} errors
 */
function run(fn, errors) {
    try {
        fn();
    } catch (error) {
        errors.push(error);
    }
}

function schedule() {
    if (!scheduled && !flushing) {
        scheduled = true;
        queueMicrotask(flush);
    }
}

/**
 * Runs `fn` with every other queued layout read, before any queued write, in
 * a microtask — after the mount/patch hooks of the current render, before
 * the browser paints — so the reads of one flush share one style
 * recalculation.
 *
 * @param {() => void} fn
 */
export function measure(fn) {
    reads.push(fn);
    schedule();
}

/**
 * Runs `fn` after every queued layout read of the flush; a write that queues
 * a read starts a second round.
 *
 * @param {() => void} fn
 */
export function mutate(fn) {
    writes.push(fn);
    schedule();
}

/** Drains both queues now, for a caller that needs the measurements before it returns. */
export function flushLayoutBatch() {
    if (reads.length || writes.length) {
        flush();
    }
}
