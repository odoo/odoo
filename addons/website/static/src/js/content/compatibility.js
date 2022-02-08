odoo.define('website.content.compatibility', function (require) {
'use strict';

/**
 * Tweaks the website rendering so that the old browsers correctly render the
 * content too.
 */

require('web.dom_ready');

// Check the browser and its version and add the info as an attribute of the
// HTML element so that css selectors can match it
var browser = _.findKey($.browser, function (v) { return v === true; });
if ($.browser.mozilla && +$.browser.version.replace(/^([0-9]+\.[0-9]+).*/, '\$1') < 20) {
    browser = 'msie';
}
browser += (',' + $.browser.version);
var mobileRegex = /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/i;
if (mobileRegex.test(window.navigator.userAgent.toLowerCase())) {
    browser += ',mobile';
}
document.documentElement.setAttribute('data-browser', browser);

// Check if flex is supported and add the info as an attribute of the HTML
// element so that css selectors can match it (only if not supported)
var htmlStyle = document.documentElement.style;
var isFlexSupported = (('flexWrap' in htmlStyle)
                    || ('WebkitFlexWrap' in htmlStyle)
                    || ('msFlexWrap' in htmlStyle));
if (!isFlexSupported) {
    document.documentElement.setAttribute('data-no-flex', '');
}

return {
    browser: browser,
    isFlexSupported: isFlexSupported,
};
});
