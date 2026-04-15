import { useSubEnv } from "@web/owl2/utils";
import { formView } from "@web/views/form/form_view";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { FormController } from "@web/views/form/form_controller";
import { onWillUnmount } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class SelectPrinterFormController extends FormController {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.onClickViewButton = this.env.onClickViewButton;

        onWillUnmount(() => {
            // If the user closes the popup without selecting a printer we still send a message back
            this.env.bus.trigger("report-printer-selected", {
                reportId: this.props.context.report_id,
                printerSettings: null,
            });
        });
        useSubEnv({ onClickViewButton: this.onClickViewButtonProxy.bind(this) });
    }

    async onClickViewButtonProxy(params) {
        const printerSettings = {
            selectedPrinters: this.model.root.evalContextWithVirtualIds.printer_ids,
            skipDialog: this.model.root.evalContextWithVirtualIds.do_not_ask_again,
        };

        if (printerSettings.selectedPrinters.length) {
            this.env.bus.trigger("report-printer-selected", {
                reportId: this.props.context.report_id,
                printerSettings,
            });
            this.onClickViewButton(params);
        } else {
            this.notification.add(_t("Please select a printer to continue"), {
                type: "danger",
            });
        }
    }
}

export const selectPrinterForm = { ...formView, Controller: SelectPrinterFormController };

registry.category("views").add("select_printer_wizard", selectPrinterForm);
