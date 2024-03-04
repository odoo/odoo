/**
 * @typedef Tour
 * @property {string} url
 * @property {string} name
 * @property {() => TourStep[]} steps
 * @property {boolean} [rainbowMan]
 * @property {number} [sequence]
 * @property {boolean} [test]
 * @property {Promise<any>} [wait_for]
 * @property {string} [saveAs]
 * @property {string} [fadeout]
 * @property {number} [checkDelay]
 * @property {string|undefined} [shadow_dom]
 */

export class Tour {
    /**
     *
     * @param {Tour} tour
     */
    constructor(tour) {
        Object.assign(this, tour);
    }
}
