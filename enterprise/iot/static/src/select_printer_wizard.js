/** @odoo-module **/

import { formView } from "@web/views/form/form_view";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { FormController } from "@web/views/form/form_controller";
import { onWillUnmount, useSubEnv } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class selectPrinterFormController extends FormController {
    setup () {
        super.setup();
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.onClickViewButton = this.env.onClickViewButton;

        onWillUnmount(() => {
            // If the user closes the popup without selecting a printer we still send a message back
            this.env.bus.trigger("printer-selected", { reportId: this.props.context.report_id, selectedPrinterIds: null });
        })
        useSubEnv({ onClickViewButton: this.onClickViewButtonIoT.bind(this) });
    }

    async onClickViewButtonIoT(params) {
        const selectedPrinterIds = this.model.root.evalContextWithVirtualIds.device_ids;
        if (selectedPrinterIds.length > 0) {
            this.env.bus.trigger("printer-selected", { reportId: this.props.context.report_id, selectedPrinterIds });
            this.onClickViewButton(params);
        } else {
            this.notification.add(_t("Select at least one printer"), {
                title: _t("No printer selected"),
                type: "danger",
            });
        }
    }
}

export const selectPrinterForm = {
    ...formView,
    Controller: selectPrinterFormController,
}

registry.category("views").add('select_printers_wizard', selectPrinterForm);
