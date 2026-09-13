// @ts-check
/** @odoo-module native */

import { SignalStore } from "@web/core/utils/reactive";

/** @typedef {Record<string, Partial<Record<string, string>>>} TransitionTable */

export class InvalidTransitionError extends Error {
    /**
     * @param {string} errorName
     * @param {string} machineName
     * @param {string} from
     * @param {string} event
     */
    constructor(errorName, machineName, from, event) {
        super(`${machineName}: invalid transition '${event}' from state '${from}'`);
        this.name = errorName;
        this.from = from;
        this.event = event;
    }
}

export class StateMachine extends SignalStore {
    /** @type {TransitionTable} */
    static transitions = {};

    /** @type {new (from: string, event: string) => Error} */
    static invalidTransitionError = class extends InvalidTransitionError {
        /**
         * @param {string} from
         * @param {string} event
         */
        constructor(from, event) {
            super("InvalidTransitionError", "StateMachine", from, event);
        }
    };

    /** @type {string} */
    status = "";

    /**
     * @param {string} event
     * @returns {void}
     */
    _transition(event) {
        const cls = /** @type {typeof StateMachine} */ (
            /** @type {unknown} */ (this.constructor)
        );
        const transitions = Object.hasOwn(cls.transitions, this.status)
            ? cls.transitions[this.status]
            : undefined;
        const next =
            transitions && Object.hasOwn(transitions, event)
                ? transitions[event]
                : undefined;
        if (next === undefined) {
            throw new cls.invalidTransitionError(this.status, event);
        }
        this.status = next;
    }
}
