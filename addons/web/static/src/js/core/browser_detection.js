odoo.define('web.BrowserDetection', function (require) {
    "use strict";

    return {
        get isOsMac() {
            return navigator.platform.toLowerCase().indexOf('mac') !== -1;
        },
        get isBrowserChrome() {
            return $.browser.chrome && // depends on jquery 1.x, removed in jquery 2 and above
                navigator.userAgent.toLocaleLowerCase().indexOf('edge') === -1; // as far as jquery is concerned, Edge is chrome
        }
    };
});

