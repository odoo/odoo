odoo.define('web.WidgetWrapper', function (require) {
    "use strict";

    const { ComponentWrapper } = require('web.OwlCompatibility');

    class WidgetWrapper extends ComponentWrapper {
        constructor() {
            super(...arguments);
        }

        //----------------------------------------------------------------------
        // Getters
        //----------------------------------------------------------------------

        get $el() {
            return $(this.el);
        }

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
