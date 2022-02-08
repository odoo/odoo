odoo.define('web.tools', function (require) {
"use strict";

/**
 * Wrapper for deprecated functions that display a warning message.
 *
 * @param {Function} fn the deprecated function
 * @param {string} [message=''] optional message to display
 * @returns {Function}
 */
function deprecated(fn, message) {
    return function () {
        console.warn(message || (fn.name + ' is deprecated.'));
        return fn.apply(this, arguments);
    };
}

return {
    deprecated: deprecated,
};

});
