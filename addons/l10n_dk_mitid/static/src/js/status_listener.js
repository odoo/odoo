import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";
import { registry } from "@web/core/registry";
import { onMounted } from "@odoo/owl";

export class MitIdStatusFormController extends FormController {
    setup() {
        super.setup();
        this.orm = this.env.services.orm;
        this.busService = this.env.services.bus_service;
        this.action = this.env.services.action;
        this.recordId = this.props.resId;

        onMounted(() => {
            this.busService.subscribe("mitid_auth_done", async (data) => {
                if (data.nemhandel_registration_id !== this.recordId) {
                    return;
                }
                const action = await this.orm.call(
                    "nemhandel.registration",
                    "display_status_notification_from_uuid",
                    [this.recordId]
                );
                this.action.doAction(action);
            });
        });
    }
}

export const mitIdStatusFormView = {
    ...formView,
    Controller: MitIdStatusFormController,
};

registry.category("views").add("mitid_status_listener", mitIdStatusFormView);
