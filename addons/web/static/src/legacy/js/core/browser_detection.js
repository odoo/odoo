/** @odoo-module **/
    import Class from "@web/legacy/js/core/class";
    import { isMacOS, isBrowserChrome } from "@web/core/browser/feature_detection";

    var BrowserDetection = Class.extend({
        init: function () {

        },
        isOsMac: isMacOS,
        isBrowserChrome,
    });
    export default BrowserDetection;
