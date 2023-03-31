/** @odoo-module alias=web.BrowserDetection **/
    import Class from "web.Class";
    import { isMacOS, isBrowserChrome } from "@web/core/browser/feature_detection";

    var BrowserDetection = Class.extend({
        init: function () {

        },
        isOsMac: isMacOS,
        isBrowserChrome,
    });
    export default BrowserDetection;
