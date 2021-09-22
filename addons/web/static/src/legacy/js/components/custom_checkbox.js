odoo.define('web.CustomCheckbox', function (require) {
    "use strict";

    const utils = require('web.utils');

    const { Component } = owl;

    /**
     * Custom checkbox
     * 
     * Component that can be used in templates to render the custom checkbox of Odoo.
     * 
     * <CustomCheckbox
     *     value="boolean"
     *     disabled="boolean"
     *     text="'Change the label text'"
     *     t-on-change="_onValueChange"
     *     />
     * 
     * @extends Component
     */
    class CustomCheckbox extends Component {
        /**
         * @param {Object} [props]
         * @param {string | number | null} [props.id]
         * @param {boolean} [props.value=false]
         * @param {boolean} [props.disabled=false]
         * @param {string} [props.text]
         */
        constructor() {
            super(...arguments);
            this._id = `checkbox-comp-${utils.generateID()}`;
        }
    }

    CustomCheckbox.props = {
        id: {
            type: [String, Number],
            optional: 1,
        },
        disabled: {
            type: Boolean,
            optional: 1,
        },
        value: {
            type: Boolean,
            optional: 1,
        },
        text: {
            type: String,
            optional: 1,
        },
    };

    CustomCheckbox.template = 'web.CustomCheckbox';

    return CustomCheckbox;
});
