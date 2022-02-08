odoo.define('event.EventConfiguratorFormController', function (require) {
"use strict";

var FormController = require('web.FormController');

/**
 * This controller is overridden to allow configuring sale_order_lines through a popup
 * window when a product with 'detailed_type' == 'event' is selected.
 *
 * This allows keeping an editable list view for sales order and remove the noise of
 * those 2 fields ('event_id' + 'event_ticket_id')
 */
var EventConfiguratorFormController = FormController.extend({
    /**
     * We let the regular process take place to allow the validation of the required fields
     * to happen.
     *
     * Then we can manually close the window, providing event information to the caller.
     *
     * @override
     */
    saveRecord: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            var state = self.renderer.state.data;
            self.do_action({type: 'ir.actions.act_window_close', infos: {
                eventConfiguration: {
                    event_id: {id: state.event_id.data.id},
                    event_ticket_id: {id: state.event_ticket_id.data.id}
                }
            }});
        });
    }
});

return EventConfiguratorFormController;

});
