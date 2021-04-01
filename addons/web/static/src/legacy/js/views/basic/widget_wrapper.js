odoo.define('web.WidgetWrapper', function (require) {
    "use strict";

    const { ComponentWrapper } = require('web.OwlCompatibility');

    class WidgetWrapper extends ComponentWrapper {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        updateState(state) {
            if (this.componentRef.comp.updateState) {
                this.componentRef.comp.updateState(state);
            }
        }
    }
    return WidgetWrapper;
});
