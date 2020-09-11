odoo.define("web.widget_registry_owl", function (require) {
    "use strict";

    const Registry = require("web.Registry");

    return new Registry(null, (value) => value.prototype instanceof owl.Component);
});
