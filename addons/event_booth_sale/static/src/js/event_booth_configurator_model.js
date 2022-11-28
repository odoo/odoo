/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { Record, RelationalModel } from "@web/views/relational_model";

/**
 * This model is overridden to allow configuring sale_order_lines through a popup
 * window when a product with 'detailed_type' == 'event_booth' is selected.
 *
 * This allows keeping an editable list view for sales order and remove the noise of
 * those 3 fields ('event_id', 'event_booth_category_id' and 'event_booth_ids')
 */
class EventBoothConfiguratorRelationalModel extends RelationalModel {}

class EventBoothConfiguratorRecord extends Record {
    //--------------------------------------------------------------------------
    // Overrides
    //--------------------------------------------------------------------------
    async save() {
        const isSaved = await super.save(...arguments);
        if (!isSaved) {
            return false;
        }
        this.model.action.doAction({type: 'ir.actions.act_window_close', infos: {
            eventBoothConfiguration: {
                event_id: this.data.event_id,
                event_booth_category_id: this.data.event_booth_category_id,
                event_booth_pending_ids: {
                    operation: 'MULTI',
                    commands: [{
                        operation: 'REPLACE_WITH',
                        ids: this.data.event_booth_ids.currentIds,
                    }],
                }
            }
        }});
        return true;
    }
}

EventBoothConfiguratorRelationalModel.Record = EventBoothConfiguratorRecord;

registry.category("views").add("event_booth_configurator_form", {
    ...formView,
    Model: EventBoothConfiguratorRelationalModel,
});
