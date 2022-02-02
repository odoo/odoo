odoo.define("root.widget", function (require) {
    require("web.legacySetup");
    const { ComponentAdapter } = require("web.OwlCompatibility");

    return Object.create(ComponentAdapter); // for its method _trigger_up
});
