/**
 * This module exists so that web_tour can use it as the parent of the
 * TourManager so it can get access to _trigger_up.
 */
odoo.define("root.widget", function (require) {
    // need to wait for owl.Component.env to be set by web.legacySetup
    require("web.legacySetup");
    const { ComponentAdapter } = require("web.OwlCompatibility");
    // Here we simply Object.create() the ComponentAdapter class
    // It is sufficient to do so as all is needed is the _trigger_up method.
    // This method uses "this.env" and if it is not set there is a fallback to
    // the owl.Component prototype env.
    //
    // NB: standaloneAdapter directly instantiate a new App accessing some env
    //     properties doing so. In the qunit test suite, web.legacySetup does not
    //     set owl.Component.env directly as a fresh new env is needed for each test.
    //     Hence using standaloneAdapter would crash.
    return Object.create(ComponentAdapter); // for its method _trigger_up
});
