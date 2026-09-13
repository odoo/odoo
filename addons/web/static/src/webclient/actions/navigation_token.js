// @ts-check
/** @odoo-module native */

import { SupersededError } from "@web/core/utils/concurrency";

export class NavigationToken {
    /**
     * @param {NavigationTracker} tracker
     * @param {number} epoch
     */
    constructor(tracker, epoch) {
        this._tracker = tracker;
        this.epoch = epoch;
    }

    /** @returns {boolean} */
    isCurrent() {
        return this._tracker.epoch === this.epoch;
    }

    /** @throws {SupersededError} */
    throwIfSuperseded() {
        if (!this.isCurrent()) {
            throw new SupersededError();
        }
    }

    /**
     * @template T
     * @param {Promise<T>} promise
     * @returns {Promise<T>}
     */
    settle(promise) {
        return this._tracker._settle(this, promise);
    }
}

export class NavigationTracker {
    constructor() {
        this._epoch = 0;
        /** @type {Set<(reason: unknown) => void>} */
        this._pendingRejects = new Set();
    }

    /** @returns {number} */
    get epoch() {
        return this._epoch;
    }

    /** @returns {NavigationToken} */
    mint() {
        this._epoch++;
        if (this._pendingRejects.size) {
            const superseded = [...this._pendingRejects];
            this._pendingRejects.clear();
            for (const reject of superseded) {
                reject(new SupersededError());
            }
        }
        return new NavigationToken(this, this._epoch);
    }

    /** @returns {NavigationToken} */
    snapshot() {
        return new NavigationToken(this, this._epoch);
    }

    /**
     * @template T
     * @param {Promise<T>} promise
     * @returns {Promise<T>}
     */
    guard(promise) {
        return this.mint().settle(promise);
    }

    /**
     * @template T
     * @param {NavigationToken} token
     * @param {Promise<T>} promise
     * @returns {Promise<T>}
     */
    _settle(token, promise) {
        return new Promise((resolve, reject) => {
            if (!token.isCurrent()) {
                promise.then(
                    () => {},
                    () => {},
                );
                reject(new SupersededError());
                return;
            }
            this._pendingRejects.add(reject);
            promise.then(
                (value) => {
                    if (token.isCurrent()) {
                        this._pendingRejects.delete(reject);
                        resolve(value);
                    }
                },
                (reason) => {
                    if (token.isCurrent()) {
                        this._pendingRejects.delete(reject);
                        reject(reason);
                    }
                },
            );
        });
    }
}
