import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";
import { registry } from "@web/core/registry";
import { onMounted } from "@odoo/owl";

export class KycStatusFormController extends FormController {
    setup() {
        super.setup();
        this.orm = this.env.services.orm;
        this.busService = this.env.services.bus_service;
        this.action = this.env.services.action;
        this.recordId = this.props.resId;

        onMounted(() => {
            this.busService.subscribe("auth_done", async (data) => {
                if (data.pdp_registration_id !== this.recordId) {
                    return;
                }
                const action = await this.orm.call(
                    "pdp.registration",
                    "display_status_notification_from_uuid",
                    [this.recordId]
                );
                this.action.doAction(action);
            });
        });
    }
}

export const kycStatusFormView = {
    ...formView,
    Controller: KycStatusFormController,
};

registry.category("views").add("pdp_status_listener", kycStatusFormView);
