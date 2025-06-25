/** @odoo-module */

import { Callbacks, HootError, createReporting, stringify } from "../hoot_utils";
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
    const parentString = parent ? ` (in parent suite ${stringify(parent.name)})` : "";
    return new HootError(
        `error while registering suite ${stringify(name)}${parentString}: ${message.join("\n")}`
    );
}

export class Suite extends Job {
    callbacks = new Callbacks();
    currentJobIndex = 0;
    /** @type {(Suite | Test)[]} */
    currentJobs = [];
    /** @type {(Suite | Test)[]} */
    jobs = [];
    reporting = createReporting();

    totalSuiteCount = 0;
    totalTestCount = 0;

    get weight() {
        return this.totalTestCount;
    }

    addJob(job) {
        this.jobs.push(job);

        if (job instanceof Suite) {
            this.increaseSuiteCount();
        } else {
            this.increaseTestCount();
        }
    }

    cleanup() {
        this.parent?.reporting.add({ suites: +1 });
        this.callbacks.clear();
    }

    increaseSuiteCount() {
        this.totalSuiteCount++;
        this.parent?.increaseSuiteCount();
    }

    increaseTestCount() {
        this.totalTestCount++;
        this.parent?.increaseTestCount();
    }

    reset() {
        this.currentJobIndex = 0;

        for (const job of this.jobs) {
            job.runCount = 0;

            if (job instanceof Suite) {
                job.reset();
            }
        }
    }

    /**
     * @param {Job[]} jobs
     */
    setCurrentJobs(jobs) {
        this.currentJobs = jobs;
        this.currentJobIndex = 0;
    }
}
