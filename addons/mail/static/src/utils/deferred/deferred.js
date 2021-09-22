/** @odoo-module **/

/**
 * @returns {Deferred}
 */
export function makeDeferred() {
    let resolve;
    let reject;
    const prom = new Promise(function (res, rej) {
        resolve = res.bind(this);
        reject = rej.bind(this);
    });
    prom.resolve = (...args) => resolve(...args);
    prom.reject = (...args) => reject(...args);
    return prom;
}
