import { proxy } from "@odoo/owl";
import { useSubEnv } from "@web/owl2/utils";
import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { useBus, useService } from "@web/core/utils/hooks";
import { FormController } from "@web/views/form/form_controller";
import { FormRenderer } from "@web/views/form/form_renderer";
import { StatusBarButtons } from "@web/views/form/status_bar_buttons/status_bar_buttons";

class MailingPreviewFormController extends FormController {
    setup() {
        super.setup();
        this.ui = useService("ui");
        const displayState = proxy({
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

class MailingPreviewStatusBar extends StatusBarButtons {
    static template = "mass_mailing.MailingPreviewStatusbar";
}

class MailingPreviewFormRenderer extends FormRenderer {
    static components = {
        ...FormRenderer.components,
        StatusBarButtons: MailingPreviewStatusBar,
    };
}

registry.category("views").add("mailing_preview_form_view", {
    ...formView,
    Controller: MailingPreviewFormController,
    Renderer: MailingPreviewFormRenderer,
});
