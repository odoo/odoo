/** @odoo-module */

import { createMock, isNil, stringToNumber } from "../hoot_utils";

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const { Math, Number, Object } = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * Returns a seeded random number generator equivalent to the native
 * {@link Math.random} method.
 *
 * It exposes a `seed` property that can be changed at any time to reset the
 * generator.
 *
 * @param {number} seed
 * @example
 *  const randA = makeSeededRandom(1e16);
 *  const randB = makeSeededRandom(1e16);
 *  randA() === randB(); // true
 * @example
 *  const random = makeSeededRandom(1e16);
 *  random() === random(); // false
 */
const makeSeededRandom = (seed) => {
    function random() {
        state ^= (state << 13) >>> 0;
        state ^= (state >>> 17) >>> 0;
        state ^= (state << 5) >>> 0;

        return ((state >>> 0) & 0x7fffffff) / 0x7fffffff; // Normalize to [0, 1)
    }

    let state = seed;

    Object.defineProperties(random, {
        seed: {
            get() {
                return seed;
            },
            set(value) {
                seed = toValidSeed(value);
                state = seed;
            },
        },
    });

    return random;
};

/**
 * @param {unknown} [seed]
 */
const toValidSeed = (seed) => {
    if (isNil(seed)) {
        return generateSeed();
    }
    const nSeed = Number(seed);
    return Number.isNaN(nSeed) ? stringToNumber(nSeed) : nSeed;
};

const DEFAULT_SEED = 1e16;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * Generates a random 16-digit number.
 * This function uses the native (unpatched) {@link Math.random} method.
 */
export function generateSeed() {
    return Math.floor(Math.random() * 1e16);
}

/**
 * @param {number} [seed]
 */
export function setRandomSeed(seed) {
    MockMath.random.seed = toValidSeed(seed);
}

export const MockMath = createMock(Math, {
    random: { value: makeSeededRandom(DEFAULT_SEED) },
});

/**
 * `random` function used internally to not generate unwanted calls on global
 * `Math.random` function (and possibly having a different seed).
 */
export const internalRandom = makeSeededRandom(DEFAULT_SEED);
