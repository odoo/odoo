/** @odoo-module */

import { reactive } from "@odoo/owl";
import { HootError } from "../hoot_utils";
import { Job } from "./job";

/**
 * @template T
 * @typedef {T | PromiseLike<T>} MaybePromise
 */

/**
 * @param {Pick<Test, "name" | "parent">} test
 * @returns {HootError}
 */
export function testError({ name, parent }, ...message) {
    const parentString = parent ? ` (in suite "${parent.name}")` : "";
    return new HootError(
        `error while registering test "${name}"${parentString}: ${message.join("\n")}`
    );
}

export class Test extends Job {
    static SKIPPED = 0;
    static PASSED = 1;
    static FAILED = 2;
    static ABORTED = 3;

    /** @type {import("./expect").TestResult[]} */
    results = reactive([]);
    status = Test.SKIPPED;
    /** @type {() => MaybePromise<void> | null} */
    run = null;

    /** @returns {typeof Test["prototype"]["results"][number]} */
    get lastResults() {
        return this.results.at(-1);
    }

    /**
     * @param {import("./suite").Suite | null} parent
     * @param {string} name
     * @param {import("./tag").Tag[]} tags
     * @param {() => MaybePromise<void>} fn
     */
    constructor(parent, name, tags, fn) {
        super(parent, name, tags);

        this.setRunFn(fn);
    }

    /**
     * @param {() => MaybePromise<void>} fn
     */
    setRunFn(fn) {
        // Makes the function async
        this.run = typeof fn === "function" ? async (...args) => fn(...args) : null;
        this.code = String(fn);
    }
}
