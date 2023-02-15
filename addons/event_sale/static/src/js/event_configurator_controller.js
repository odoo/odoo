/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formView } from "@web/views/form/form_view";

/**
 * This controller is overridden to allow configuring sale_order_lines through a popup
 * window when a product with 'detailed_type' == 'event' is selected.
 *
 * This allows keeping an editable list view for sales order and remove the noise of
 * those 2 fields ('event_id' + 'event_ticket_id')
 */

class EventConfiguratorController extends formView.Controller {
    setup() {
        super.setup();
        this.action = useService("action");
    }

    /**
     * We let the regular process take place to allow the validation of the required fields
     * to happen.
     *
     * Then we can manually close the window, providing event information to the caller.
     *
     * @override
     */
    onRecordSaved(record) {
        const { event_id, event_ticket_id } = record.data;
        return this.action.doAction({
            type: "ir.actions.act_window_close",
            infos: {
                eventConfiguration: {
                    event_id,
                    event_ticket_id,
                },
            },
        });
    }
}

registry.category("views").add("event_configurator_form", {
    ...formView,
    Controller: EventConfiguratorController,
});
