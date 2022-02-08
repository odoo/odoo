odoo.define('web.BrowserDetection', function (require) {
    "use strict";
    var Class = require('web.Class');
    const { isMacOS, isBrowserChrome } = require('@web/core/browser/feature_detection');

    var BrowserDetection = Class.extend({
        init: function () {

        },
        isOsMac: isMacOS,
        isBrowserChrome,
    });
    return BrowserDetection;
});

