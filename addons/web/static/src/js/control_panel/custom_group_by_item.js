odoo.define('web.CustomGroupByItem', function (require) {
    "use strict";

    const DropdownMenuItem = require('web.DropdownMenuItem');
    const { useModel } = require('web/static/src/js/model.js');
    const { onWillUpdateProps } = owl.hooks;

    /**
     * Group by generator menu
     *
     * Component used to generate new filters of type 'groupBy'. It is composed
     * of a button (used to toggle the rendering of the rest of the component) and
     * an input (select) used to choose a new field name which will be used as a
     * new groupBy value.
     * @extends DropdownMenuItem
     */
    class CustomGroupByItem extends DropdownMenuItem {
        constructor() {
            super(...arguments);

            this.canBeOpened = true;
            this.state.fieldName = this.props.fields[0].name;

            this.model = useModel('searchModel');

            onWillUpdateProps((nextProps) => {
                this.state.fieldName = nextProps.fields[0].name;
            });
        }

        //---------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------

        /**
         * @private
         */
        _onApply() {
            const field = this.props.fields.find(f => f.name === this.state.fieldName);
            this.model.dispatch('createNewGroupBy', field);
            this.state.open = false;
            this.trigger('custom-group-applied');
        }
    }

    CustomGroupByItem.template = 'web.CustomGroupByItem';
    CustomGroupByItem.props = {
        fields: Array,
    };

    return CustomGroupByItem;
});
