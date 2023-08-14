odoo.define('mrp.should_consume', function (require) {
"use strict";

const BasicFields = require('web.basic_fields');
const FieldFloat = BasicFields.FieldFloat;
const fieldRegistry = require('web.field_registry');
const field_utils = require('web.field_utils');

/**
 * This widget is used to display alongside the total quantity to consume of a production order,
 * the exact quantity that the worker should consume depending on the BoM. Ex:
 * 2 components to make 1 finished product.
 * The production order is created to make 5 finished product and the quantity producing is set to 3.
 * The widget will be '3.000 / 5.000'.
 */
const MrpShouldConsume = FieldFloat.extend({
    /**
     * @override
     */
    init: function (parent, name, params) {
        this._super.apply(this, arguments);
        this.displayShouldConsume = !['done', 'draft', 'cancel'].includes(params.data.state);
        this.should_consume_qty = field_utils.format.float(params.data.should_consume_qty, params.fields.should_consume_qty, this.nodeOptions);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Prefix the classic float field (this.$el) by a static value.
     *
     * @private
     * @param {float} [value] quantity to display before the input `el`
     * @param {bool} [edit] whether the field will be editable or readonly
     */
    _addShouldConsume: function (value, edit=false) {
        const $to_consume_container = $('<span class="o_should_consume"/>');
        if (edit) {
            $to_consume_container.addClass('o_row');
        }
        $to_consume_container.text(value + ' / ');
        this.setElement(this.$el.wrap($to_consume_container).parent());
    },

    /**
     * @private
     * @override
     */
    _renderEdit: function () {
        if (this.displayShouldConsume) {
            if (!this.$el.text().includes('/')) {
                this.$input = this.$el;
                this._addShouldConsume(this.should_consume_qty, true);
            }
            this._prepareInput(this.$input);
        } else {
            this._super.apply(this);
        }
    },
    /**
     * Resets the content to the formated value in readonly mode.
     *
     * @override
     * @private
     */
    _renderReadonly: function () {
        this.$el.text(this._formatValue(this.value));
        if (this.displayShouldConsume) {
            this._addShouldConsume(this.should_consume_qty);
        }
    },
});

fieldRegistry.add('mrp_should_consume', MrpShouldConsume);

return {
    MrpShouldConsume: MrpShouldConsume,
};

});
