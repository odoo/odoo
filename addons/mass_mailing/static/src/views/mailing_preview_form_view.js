import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { useBus, useService } from "@web/core/utils/hooks";
import { reactive, useSubEnv } from "@odoo/owl";
import { FormController } from "@web/views/form/form_controller";

class MailingPreviewFormController extends FormController {
    setup() {
        super.setup();
        this.ui = useService("ui");
        const displayState = reactive({
            isMobileMode: this.ui.isSmall,
            isSmall: this.ui.isSmall,
        });

        useSubEnv({ displayState });

        useBus(this.ui.bus, "resize", () => {
            displayState.isSmall = this.ui.isSmall;
            if (displayState.isSmall) {
                displayState.isMobileMode = true;
            }
        });
    }
}

registry.category("views").add("mailing_preview_form_view", {
    ...formView,
    Controller: MailingPreviewFormController,
});
