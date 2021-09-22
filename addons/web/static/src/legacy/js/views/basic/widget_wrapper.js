odoo.define('web.WidgetWrapper', function (require) {
    "use strict";

    const { ComponentWrapper } = require('web.OwlCompatibility');

    class WidgetWrapper extends ComponentWrapper {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * This function should be used to update the "widget" Component's props,
         * not its state!
         *
         * @param {any} state
         * @returns Promise
         */
        updateState(state) {
            return this.update(Object.assign({}, this.props, { record: state }));
        }
    }
    return WidgetWrapper;
});
