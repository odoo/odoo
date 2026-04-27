/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";

import { useAddPayslips } from '../add_payslips_hook.js';

export class PayslipBatchFormController extends FormController {
    setup() {
        super.setup();
        this.addPayslips = useAddPayslips();
    }

    getStaticActionMenuItems() {
        const menuItems = super.getStaticActionMenuItems();

        if (['draft', 'verify'].includes(this.model.root.data.state)) {
            menuItems.add_payslips = {
                sequence: 50,
                description: _t('Add Payslips'),
                callback: async () => {
                    await this.addPayslips(this.model.root);
                },
            };
        }

        return menuItems;
    }
}

registry.category("views").add("hr_payslip_batch_form", {
    ...formView,
    Controller: PayslipBatchFormController,
});
