odoo.define('web.widget_registry', function (require) {
    "use strict";

    ////////////////////////////////////////////////////////////////////////////
    // /!\ DEPRECATED
    //
    // /!\ This registry is deprecated. It is used to register legacy Widgets.
    // /!\ Use 'web.widgetRegistry' to register Owl Components.
    // /!\ Existing Widgets will be at some point converted into Owl Components.
    // /!\ All new code should be directly written using Owl Components.
    ////////////////////////////////////////////////////////////////////////////


    // This registry is supposed to contain all custom widgets that will be
    // available in the basic views, with the tag <widget/>.  There are
    // currently no such widget in the web client, but the functionality is
    // certainly useful to be able to cleanly add custom behaviour in basic
    // views (and most notably, the form view)
    //
    // The way custom widgets work is that they register themselves to this
    // registry:
    //
    // widgetRegistry.add('some_name', MyWidget);
    //
    // Then, they are available with the <widget/> tag (in the arch):
    //
    // <widget name="some_name"/>
    //
    // Widgets will be then properly instantiated, rendered and destroyed at the
    // appropriate time, with the current state in second argument.
    //
    // For more examples, look at the tests (grep '<widget' in the test folder)

    var Registry = require('web.Registry');

    return new Registry(null, (value) => !(value.prototype instanceof owl.Component));
});
