/** @odoo-module */

import { reactive } from "@odoo/owl";
import { HootError, stringify } from "../hoot_utils";
import { Job } from "./job";
import { Tag } from "./tag";

/**
 * @template T
 * @typedef {T | PromiseLike<T>} MaybePromise
 */

/**
 * @param {Pick<Test, "name" | "parent">} test
 * @returns {HootError}
 */
export function testError({ name, parent }, ...message) {
    const parentString = parent ? ` (in suite ${stringify(parent.name)})` : "";
    return new HootError(
        `error while registering test ${stringify(name)}${parentString}: ${message.join("\n")}`
    );
}

export class Test extends Job {
    static SKIPPED = 0;
    static PASSED = 1;
    static FAILED = 2;
    static ABORTED = 3;

    formattedCode = "";
    logs = reactive({
        error: 0,
        warn: 0,
    });
    /** @type {import("./expect").TestResult[]} */
    results = reactive([]);
    /** @type {() => MaybePromise<void> | null} */
    run = null;
    /** @type {string} */
    runFnString = "";
    status = Test.SKIPPED;

    get code() {
        if (!this.formattedCode) {
            this.formattedCode = this.formatFunctionSource();
        }
        return this.formattedCode;
    }

    /** @returns {typeof Test["prototype"]["results"][number]} */
    get lastResults() {
        return this.results.at(-1);
    }

    /**
     * @param {() => MaybePromise<void>} fn
     */
    setRunFn(fn) {
        this.run = fn ? async () => fn() : null;
        if (fn) {
            this.runFnString = fn.toString();
        }
    }

    formatFunctionSource() {
        let stringFn = this.runFnString;
        if (this.name) {
            let prefix = "";
            const tags = [];
            for (const tag of this.tags) {
                if (this.parent.tags.includes(tag)) {
                    continue;
                }
                switch (tag.key) {
                    case Tag.TODO:
                    case Tag.DEBUG:
                    case Tag.SKIP:
                    case Tag.ONLY: {
                        prefix += `.${tag.key}`;
                        break;
                    }
                    default: {
                        tags.push(stringify(tag.name));
                    }
                }
            }
            if (tags.length) {
                prefix += `.tags(${tags.join(", ")})`;
            }

            stringFn = `test${prefix}(${stringify(this.name)}, ${stringFn});`;
        }

        const lines = stringFn.split("\n");

        let toTrim = null;
        for (let i = 1; i < lines.length; i++) {
            if (!lines[i].trim()) {
                continue;
            }
            const [, whiteSpaces] = lines[i].match(/^(\s*)/);
            if (toTrim === null || whiteSpaces.length < toTrim) {
                toTrim = whiteSpaces.length;
            }
        }
        if (toTrim) {
            for (let i = 1; i < lines.length; i++) {
                lines[i] = lines[i].slice(toTrim);
            }
        }

        return lines.join("\n");
    }
}
