odoo.define('website.helpers', function (require) {
'use strict';

/**
 * Remove the query string and/or anchor from a url
 *
 * @param {String} url
 * @param {boolean} removeQueryString: remove the query string (after ?)
 * @param {boolean} removeAnchor: remove the anchor (after #)
 */
function cleanUrl(url, removeQueryString, removeAnchor) {
    removeQueryString = typeof removeQueryString === 'undefined' ? true : !!removeQueryString;
    removeAnchor = typeof removeAnchor === 'undefined' ? true : !!removeAnchor;

    // For anchor we remove everything after "#", even "?" (query string is supposed to be before)
    var hashIndex = url.indexOf('#');
    if (removeAnchor) {
        url = hashIndex >= 0 ? url.substring(0, hashIndex) : url;
        hashIndex = -1;
    }

    // For query string we remove everything after "?", but before "#" if present
    if (removeQueryString) {
        var queryStringIndex = url.indexOf('?');
        if (queryStringIndex >= 0) {
            if (hashIndex === -1 || queryStringIndex < hashIndex) {
                var beforeQueryString = url.substring(0, queryStringIndex);
                var afterQueryString = hashIndex >= 0 ? url.substring(hashIndex) : '';
                url = beforeQueryString + afterQueryString;
            }
        }
    }
    return url;
}

return {
    cleanUrl: cleanUrl,
};
});
