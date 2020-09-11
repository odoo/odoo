odoo.define("web.widgetRegistry", function (require) {
    "use strict";

    // This registry is supposed to contain all custom components that will be
    // available in the basic views, with the tag <widget/>. Those components
    // allow to cleanly add custom behavior in basic views.
    //
    // The way custom components work is that they register themselves to this
    // registry:
    //
    //     widgetRegistry.add('some_name', MyComponent);
    //
    // Then, they are available with the <widget/> tag (in the arch):
    //
    //     <widget name="some_name"/>
    //
    // Those components will be then properly instantiated, rendered and
    // destroyed at the appropriate time, and will receive the current state in
    // props.

    const Registry = require("web.Registry");

    return new Registry(null, (value) => value.prototype instanceof owl.Component);
});
