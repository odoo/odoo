odoo.define('mrp.should_consume', function (require) {
"use strict";

var BasicFields = require('web.basic_fields');
var FieldFloat = BasicFields.FieldFloat;
var fieldRegistry = require('web.field_registry');
var field_utils = require('web.field_utils');

/**
 * This widget is used to display alongside the total quantity to consume of a production order,
 * the exact quantity that the worker should consume depending on the BoM. Ex:
 * 2 components to make 1 finished product.
 * The production order is created to make 5 finished product and the quantity producing is set to 3.
 * The widget will be '3.000 / 5.000'.
 */
var MrpShouldConsume = FieldFloat.extend({
    /**
     * @override
     */
    init: function (parent, name, params) {
        this._super.apply(this, arguments);
        this.displayShouldConsume = !['done', 'draft', 'cancel'].includes(params.data.state);
        let options = {'digits': [false, 3]};
        this.should_consume_qty = field_utils.format.float(params.data.should_consume_qty, false, options);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} [el] jquery input element that will be surrounded by a new span
     * @param {float} [value] quantity to display before the input `el`
     * @return {jquery element}
     */
    _addShouldConsume: function (el, value) {
        var $to_consume_container = $('<span class="o_should_consume"/>');
        $to_consume_container.text(value + ' / ');
        $to_consume_container.append(el);
        return $to_consume_container
    },

    /**
     * @private
     * @override
     */
    _renderEdit: function () {
        // Keep a reference to the input so $el can become something else
        // without losing track of the actual input.
        var def = this._super.apply(this, arguments);
        if (this.displayShouldConsume) {
            var $container = this._addShouldConsume(this.$el, this.should_consume_qty);
            $container.addClass('o_row');
            this.$el = $container;
        };
        return def;
    },
    /**
     * Resets the content to the formated value in readonly mode.
     *
     * @override
     * @private
     */
    _renderReadonly: function () {
        var def = this._super.apply(this, arguments);
        if (this.displayShouldConsume) {
            var $container = this._addShouldConsume(this.$el, this.should_consume_qty);
            this.$el = $container;
        };
        return def;
    },
});

fieldRegistry.add('mrp_should_consume', MrpShouldConsume);

return {
    MrpShouldConsume: MrpShouldConsume,
};

});
