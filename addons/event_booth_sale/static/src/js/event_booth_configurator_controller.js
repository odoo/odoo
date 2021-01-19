odoo.define('event_booth_sale.event_booth_configurator_form_controller', function (require) {
'use strict';

var FormController = require('web.FormController');

/**
 * This controller is overridden to allow configuring sale_order_lines through a popup
 * window when a product with 'is_event_booth' is selected.
 *
 * This allows keeping an editable list view for sales order and remove the noise of
 * those 3 fields ('event_id', 'event_booth_id' and 'event_booth_slot_ids')
 */
var EventBoothConfiguratorFormController = FormController.extend({

    saveRecord: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            const state = self.model.get(self.handle, {raw: true});
            self.do_action({
                type: 'ir.actions.act_window_close',
                infos: {
                    eventBoothConfiguration: {
                        event_id: {id: state.data.event_id},
                        event_booth_id: {id: state.data.event_booth_id},
                        event_booth_slot_ids: {
                            operation: 'MULTI',
                            commands: [{
                                operation: 'REPLACE_WITH',
                                ids: state.data.event_booth_slot_ids}]
                        }
                    }
                }
            });
        });
    }
});

return EventBoothConfiguratorFormController;

});
