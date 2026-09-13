// @ts-check
/** @odoo-module native */

import { ModelEvent } from "@web/core/events";
import { InvalidTransitionError, StateMachine } from "@web/core/utils/state_machine";

/**
 * @typedef {"idle" | "active"} UrgentSaveStatus
 * @typedef {"begin" | "end"} UrgentSaveEvent
 */

/** @type {Record<UrgentSaveStatus, Partial<Record<UrgentSaveEvent, UrgentSaveStatus>>>} */
const TRANSITIONS = {
    idle: { begin: "active" },
    active: { end: "idle" },
};

const REENTRANT_DRAIN_MAX_ROUNDS = 100;

class InvalidUrgentSaveTransitionError extends InvalidTransitionError {
    /**
     * @param {string} from
     * @param {string} event
     */
    constructor(from, event) {
        super("InvalidUrgentSaveTransitionError", "UrgentSaveCoordinator", from, event);
    }
}

export class UrgentSaveCoordinator extends StateMachine {
    static transitions = TRANSITIONS;
    static invalidTransitionError = InvalidUrgentSaveTransitionError;

    /** @param {{ trigger: (event: string, payload?: any) => void } | null} [bus] */
    constructor(bus = null) {
        super();
        /** @type {UrgentSaveStatus} */
        this.status = "idle";
        this._bus = bus;
        /** @type {Promise<unknown>[]} */
        this._reentrantProms = [];
    }

    /** @returns {boolean} */
    get isActive() {
        return this.status === "active";
    }

    /**
     * @template T
     * @param {() => Promise<T>} fn
     * @returns {Promise<T>}
     */
    async run(fn) {
        if (this.isActive) {
            const prom = fn();
            this._reentrantProms.push(prom);
            return prom;
        }
        this._transition("begin");
        this._reentrantProms = [];
        /** @type {Promise<any>[]} */
        const proms = [];
        try {
            try {
                this._bus?.trigger(ModelEvent.WILL_SAVE_URGENTLY, { proms });
            } finally {
                // A hook may register work before throwing. Observe that work
                // on the failure path too, then restore the coordinator below.
                await Promise.allSettled(proms);
            }
            return await fn();
        } finally {
            let rounds = 0;
            while (this._reentrantProms.length) {
                if (rounds++ >= REENTRANT_DRAIN_MAX_ROUNDS) {
                    console.warn(
                        `UrgentSaveCoordinator: reentrant saves did not settle ` +
                            `after ${REENTRANT_DRAIN_MAX_ROUNDS} rounds; ` +
                            `${this._reentrantProms.length} still in flight. ` +
                            `Ending the urgent save anyway -- this runs inside a ` +
                            `beforeunload handler, where blocking forever costs ` +
                            `the user the whole tab.`,
                    );
                    break;
                }
                const reentrant = this._reentrantProms;
                this._reentrantProms = [];
                await Promise.allSettled(reentrant);
            }
            this._reentrantProms = [];
            this._transition("end");
        }
    }

    flushPendingEdits() {
        return this.run(() => Promise.resolve());
    }

    /**
     * @template T
     * @param {Promise<T> | undefined} promise
     * @returns {Promise<T | undefined>}
     */
    async awaitUnlessUrgent(promise) {
        if (this.isActive) {
            Promise.resolve(promise).catch(() => {});
            return undefined;
        }
        return promise;
    }

    /**
     * @template T
     * @param {() => T | Promise<T>} fn
     * @returns {T | undefined | Promise<T>}
     */
    unlessUrgent(fn) {
        if (this.isActive) {
            return undefined;
        }
        return fn();
    }
}
