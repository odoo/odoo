/** @odoo-module */
/* eslint-disable no-restricted-syntax */

import { reactive } from "@odoo/owl";
import { HootError } from "../hoot_utils";
import { Job } from "./job";

/**
 * @template T
 * @typedef {T | PromiseLike<T>} MaybePromise
 */

/**
 * @param {Function} fn
 */
const formatFunctionSource = (fn) => {
    const lines = String(fn).split("\n");

    if (lines.length > 2) {
        lines.shift();
        lines.pop();
    }

    let toTrim = null;
    for (const line of lines) {
        if (!line.trim()) {
            continue;
        }
        const [, whiteSpaces] = line.match(/^(\s*)/);
        if (toTrim === null || whiteSpaces.length < toTrim) {
            toTrim = whiteSpaces.length;
        }
    }
    if (toTrim) {
        for (let i = 0; i < lines.length; i++) {
            lines[i] = lines[i].slice(toTrim);
        }
    }

    return lines.join("\n");
};

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

    code = "";
    /** @type {import("./expect").TestResult[]} */
    results = reactive([]);
    /** @type {() => MaybePromise<void> | null} */
    runFn = null;
    status = Test.SKIPPED;

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
     * @param {...unknown} args
     */
    async run(...args) {
        return this.runFn(...args);
    }

    /**
     * @param {() => MaybePromise<void>} fn
     */
    setRunFn(fn) {
        this.runFn = fn;
        if (this.runFn) {
            this.code = formatFunctionSource(this.runFn);
        }
    }
}
