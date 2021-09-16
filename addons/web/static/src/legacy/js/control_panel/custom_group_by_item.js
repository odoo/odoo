odoo.define('web.CustomGroupByItem', function (require) {
    "use strict";

    const { useModel } = require('web.Model');

    const { Component, hooks } = owl;
    const { useState } = hooks;

    class CustomGroupByItem extends Component {
        constructor() {
            super(...arguments);

            this.state = useState({
                fieldName: this.props.fields[0].name,
            });

            this.model = useModel('searchModel');
        }

        //---------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------

        /**
         * @private
         */
        onApply() {
            const field = this.props.fields.find(f => f.name === this.state.fieldName);
            this.model.dispatch('createNewGroupBy', field);
        }
    }

    CustomGroupByItem.template = "web.CustomGroupByItem";
    CustomGroupByItem.props = {
        fields: Array,
    };

    return CustomGroupByItem;
});
