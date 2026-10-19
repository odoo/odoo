import { onWillUnmount } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";
import {
    provideViewButtonHandler,
    useViewButtonHandler,
} from "@web/views/view_button/view_button_hook";

export class SelectPrintersWizard extends FormController {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.printersCache = useService("report_printers_cache");
        this.onClickViewButton = useViewButtonHandler();

        onWillUnmount(() => {
            // If the user closes the popup without selecting a printer we still send a message back
            this.env.bus.trigger("printer-selected", {
                reportId: this.props.context.report_id,
                deviceSettings: null,
            });
        });
        provideViewButtonHandler(this.onClickPrinterSelectionSaveButton.bind(this));
    }

    get extractSettings() {
        const { printer_ids, do_not_ask_again } = this.model.root.evalContextWithVirtualIds;
        return {
            selectedPrinters: this.props.context.printer_ids.filter((p) =>
                printer_ids.includes(p.id)
            ),
            skipDialog: do_not_ask_again,
        };
    }

    async onClickPrinterSelectionSaveButton(params) {
        const deviceSettings = this.extractSettings;
        if (deviceSettings.selectedPrinters.length > 0) {
            this.env.bus.trigger("printer-selected", {
                reportId: this.props.context.report_id,
                deviceSettings,
            });
            this.onClickViewButton(params);
        } else {
            this.notification.add(_t("Select at least one printer"), {
                type: "danger",
            });
        }
    }
}

export const selectPrinterForm = {
    ...formView,
    Controller: SelectPrintersWizard,
};

registry.category("views").add("select_printers_wizard", selectPrinterForm);
