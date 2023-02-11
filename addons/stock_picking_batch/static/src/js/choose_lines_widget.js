odoo.define('stock_picking_wave.choose_lines_widget', function (require) {
const relationalFields = require('web.relational_fields');
const FieldsRegistry = require('web.field_registry');
const core = require('web.core');

var ChoosePickingWidget = relationalFields.FieldOne2Many.extend({

    init: function (parent, name, record, options) {
        this._super.apply(this, arguments);
        this.isMany2Many = true;
        this.isWave = record.data.is_wave;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------
    /**
     * Opens a SelectCreateDialog
     */
    _setValue: function (value, options) {
        return this._super(value, options).then(() => {
            if (value.operation === 'ADD_M2M') {
                core.bus.trigger('add_move_lines', value.ids);
            }
        });
    },

});

var ChooseLinesWidget = relationalFields.FieldMany2Many.extend({

    start: function () {
        core.bus.on('add_move_lines', this, this.onAddRecordOpenDialog);
        return this._super();
    },
});

FieldsRegistry.add('choose_lines_widget', ChooseLinesWidget);
FieldsRegistry.add('choose_picking_widget', ChoosePickingWidget);

return ChooseLinesWidget, ChoosePickingWidget;

});
