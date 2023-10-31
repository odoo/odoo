odoo.define('fleet.fleet_kanban', function (require) {
    'use strict';

    const KanbanRecord = require('web.KanbanRecord');

    KanbanRecord.include({

        /**
         * @override
         * @private
         */
        _openRecord() {
            if (this.modelName === 'fleet.vehicle.model.brand' && this.$(".oe_kanban_fleet_model").length) {
                this.$('.oe_kanban_fleet_model').first().click();
            } else {
                this._super.apply(this, arguments);
            }
        },
    });
});
