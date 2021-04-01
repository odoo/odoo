odoo.define('web.BrowserDetection', function (require) {
    "use strict";
    var Class = require('web.Class');

    var BrowserDetection = Class.extend({
        init: function () {

        },
        isOsMac: function () {
            return navigator.platform.toLowerCase().indexOf('mac') !== -1;
        },
        isBrowserChrome: function () {
            return $.browser.chrome && // depends on jquery 1.x, removed in jquery 2 and above
                navigator.userAgent.toLocaleLowerCase().indexOf('edge') === -1; // as far as jquery is concerned, Edge is chrome
            }

    });
    return BrowserDetection;
});

