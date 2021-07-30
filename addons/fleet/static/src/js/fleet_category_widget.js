odoo.define('fleet.many2one_fleet_category', function (require) {
"use strict;"

const relationalFields = require('web.relational_fields');
const FieldMany2One = relationalFields.FieldMany2One;
const FieldRegistry = require('web.field_registry');

const FieldMany2OneFleetCategory = FieldMany2One.extend({
    /**
     * Opens the list view on the vehicles in the fleet instead of the form view
     *
     * @param {*} event
     * @private
     */
    _onClick: function (event) {
        var self = this;
        if (this.mode === 'readonly') {
            event.preventDefault();
            if (this.noOpen) {
                this._super(...arguments);
            } else {
                event.stopPropagation();
                this._rpc({
                    model: 'fleet.category',
                    method: 'action_view_vehicles',
                    args: [[this.value.res_id]],
                }).then(function (action) {
                    self.trigger_up('do_action', {action: action});
                });
            }
        }
    }
})

FieldRegistry.add('many2one_fleet_category', FieldMany2OneFleetCategory);
return FieldMany2OneFleetCategory;
});
