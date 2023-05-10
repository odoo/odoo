/**
 * @template T
 * @typedef {{ [k in keyof T]: T[k] } & {}} Prettify
 */

/**
 * @typedef {Prettify<{ a: number } & { b: boolean }>} asd
 */

/**
 * @type {asd}
 */
const a = {};