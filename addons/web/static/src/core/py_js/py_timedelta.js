// @ts-check

/** @module @web/core/py_js/py_timedelta - Python timedelta emulation: normalized duration stored as (days, seconds, microseconds) */

import { divmod } from "./py_date_helpers";
import { parseArgs } from "./py_parser";

const TIME_DELTA_KEYS =
    "weeks days hours minutes seconds milliseconds microseconds".split(" ");

/**
 * Returns a "pair" with the fractional and integer parts of x.
 * @param {number} x
 * @returns {[number, number]}
 */
function modf(x) {
    const mod = x % 1;
    return [mod < 0 ? mod + 1 : mod, Math.floor(x)];
}

export class PyTimeDelta {
    /**
     * @param  {...any} args
     * @returns {PyTimeDelta}
     */
    static create(...args) {
        const namedArgs = parseArgs(args, ["days", "seconds", "microseconds"]);
        for (const key of TIME_DELTA_KEYS) {
            namedArgs[key] = namedArgs[key] || 0;
        }

        // a timedelta can be created using TIME_DELTA_KEYS with float/integer values
        // but only days, seconds, microseconds are kept internally.
        // --> some normalization occurs here

        let d = 0;
        let s = 0;
        let us = 0; // ~ μs standard notation for microseconds

        const days = namedArgs.days + namedArgs.weeks * 7;
        let seconds =
            namedArgs.seconds + 60 * namedArgs.minutes + 3600 * namedArgs.hours;
        let microseconds = namedArgs.microseconds + 1000 * namedArgs.milliseconds;

        const [dFrac, dInt] = modf(days);
        d = dInt;
        let daysecondsfrac = 0;
        if (dFrac) {
            const [dsFrac, dsInt] = modf(dFrac * 24 * 3600);
            s = dsInt;
            daysecondsfrac = dsFrac;
        }

        const [sFrac, sInt] = modf(seconds);
        seconds = sInt;
        const secondsfrac = sFrac + daysecondsfrac;

        divmod(seconds, 24 * 3600, (days, seconds) => {
            d += days;
            s += seconds;
        });

        microseconds += secondsfrac * 1e6;
        divmod(microseconds, 1000000, (seconds, microseconds) => {
            divmod(seconds, 24 * 3600, (days, seconds) => {
                d += days;
                s += seconds;
                us += Math.round(microseconds);
            });
        });

        return new PyTimeDelta(d, s, us);
    }

    /**
     * @param {number} days
     * @param {number} seconds
     * @param {number} microseconds
     */
    constructor(days, seconds, microseconds) {
        this.days = days;
        this.seconds = seconds;
        this.microseconds = microseconds;
    }

    /**
     * @param {PyTimeDelta} other
     * @returns {PyTimeDelta}
     */
    add(other) {
        return PyTimeDelta.create({
            days: this.days + other.days,
            seconds: this.seconds + other.seconds,
            microseconds: this.microseconds + other.microseconds,
        });
    }

    /**
     * @param {number} n
     * @returns {PyTimeDelta}
     */
    divide(n) {
        const us = (this.days * 24 * 3600 + this.seconds) * 1e6 + this.microseconds;
        return PyTimeDelta.create({ microseconds: Math.floor(us / n) });
    }

    /**
     * @param {any} other
     * @returns {boolean}
     */
    isEqual(other) {
        if (!(other instanceof PyTimeDelta)) {
            return false;
        }
        return (
            this.days === other.days &&
            this.seconds === other.seconds &&
            this.microseconds === other.microseconds
        );
    }

    /** @returns {boolean} */
    isTrue() {
        return this.days !== 0 || this.seconds !== 0 || this.microseconds !== 0;
    }

    /**
     * @param {number} n
     * @returns {PyTimeDelta}
     */
    multiply(n) {
        return PyTimeDelta.create({
            days: n * this.days,
            seconds: n * this.seconds,
            microseconds: n * this.microseconds,
        });
    }

    /** @returns {PyTimeDelta} */
    negate() {
        return PyTimeDelta.create({
            days: -this.days,
            seconds: -this.seconds,
            microseconds: -this.microseconds,
        });
    }

    /**
     * @param {PyTimeDelta} other
     * @returns {PyTimeDelta}
     */
    substract(other) {
        return PyTimeDelta.create({
            days: this.days - other.days,
            seconds: this.seconds - other.seconds,
            microseconds: this.microseconds - other.microseconds,
        });
    }

    /** @returns {number} */
    total_seconds() {
        return this.days * 86400 + this.seconds + this.microseconds / 1000000;
    }
}
