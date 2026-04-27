/** @odoo-module **/

import { download } from "@web/core/network/download";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class GenerateCommissionPayslipsFormController extends FormController {
    setup(){
        super.setup();
        this.orm = useService("orm");
    }

    /**
     * @override
     */
    async beforeExecuteActionButton(clickParams) {
        if (clickParams.name === 'export_warrant_payslips') {
            if (this.props.saveRecord) {
                await this.props.saveRecord(this.model.root, { stayInEdit: true });
            } else {
                await this.model.root.save({ stayInEdit: true });
            }
            await this.downloadExportedCSV();
            return false;
        }
        return super.beforeExecuteActionButton(...arguments);
    }

    async downloadExportedCSV() {
        const recordId = this.model.root.resId;
        await download({
            url: `/export/warrant_payslips/${recordId}`,
            data: {}
        });
        await this.model.root.load();
        this.model.notify();
        await this.model.root.switchMode("edit");
    }
}

registry.category("views").add('generate_warrant_payslips', {
    ...formView,
    Controller: GenerateCommissionPayslipsFormController
})
