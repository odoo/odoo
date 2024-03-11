/**
 * This module exists so that web_tour can use it as the parent of the
 * TourManager so it can get access to _trigger_up.
 */
odoo.define("root.widget", function (require) {
    // need to wait for owl.Component.env to be set by web.legacySetup
    require("web.legacySetup");
    const { ComponentAdapter } = require("web.OwlCompatibility");
    // for its method _trigger_up. We can't use a standalone adapter because it
    // attempt to call env.isDebug which is not defined in the tests when this
    // module is loaded.
    return new ComponentAdapter({ Component: owl.Component }, owl.Component.env);
});
