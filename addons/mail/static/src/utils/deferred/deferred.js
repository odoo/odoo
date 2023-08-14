odoo.define('mail/static/src/utils/deferred/deferred.js', function (require) {
'use strict';

/**
 * @returns {Deferred}
 */
function makeDeferred() {
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

return { makeDeferred };

});
