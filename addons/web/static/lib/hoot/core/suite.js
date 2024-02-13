/** @odoo-module */

import { HootError, createReporting, makeCallbacks } from "../hoot_utils";
import { Job } from "./job";

/**
 * @typedef {import("./tag").Tag} Tag
 *
 * @typedef {import("./test").Test} Test
 */

/**
 * @param {Pick<Suite, "name" | "parent">} suite
 * @param {...string} message
 * @returns {HootError}
 */
export function suiteError({ name, parent }, ...message) {
    const parentString = parent ? ` (in parent suite "${parent.name}")` : "";
    return new HootError(
        `error while registering suite "${name}"${parentString}: ${message.join("\n")}`
    );
}

export class Suite extends Job {
    callbacks = makeCallbacks();
    /** @type {(Suite | Test)[]} */
    currentJobs = [];
    /** @type {(Suite | Test)[]} */
    jobs = [];
    reporting = createReporting();
    weight = 0;

    /**
     * @returns {boolean}
     */
    canRun() {
        return super.canRun() && this.currentJobs.some((job) => job.canRun());
    }

    increaseWeight() {
        this.weight++;
        if (this.parent) {
            this.parent.increaseWeight();
        }
    }
}
