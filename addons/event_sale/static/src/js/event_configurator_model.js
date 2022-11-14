/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { Record, RelationalModel } from "@web/views/relational_model";

/**
 * This model is overridden to allow configuring sale_order_lines through a popup
 * window when a product with 'detailed_type' == 'event' is selected.
 *
 * This allows keeping an editable list view for sales order and remove the noise of
 * those 2 fields ('event_id' + 'event_ticket_id')
 */

class EventConfiguratorRelationalModel extends RelationalModel {}

class EventConfiguratorRecord extends Record {
    /**
     * We let the regular process take place to allow the validation of the required fields
     * to happen.
     *
     * Then we can manually close the window, providing event information to the caller.
     *
     * @override
     */
    async save() {
        const isSaved = await super.save(...arguments);
        if (!isSaved) {
            return false;
        }
        this.model.action.doAction({type: 'ir.actions.act_window_close', infos: {
            eventConfiguration: {
                event_id: this.data.event_id,
                event_ticket_id: this.data.event_ticket_id,
            }
        }});
        return true;
    }
}

EventConfiguratorRelationalModel.Record = EventConfiguratorRecord;

registry.category("views").add("event_configurator_form", {
    ...formView,
    Model: EventConfiguratorRelationalModel,
});
