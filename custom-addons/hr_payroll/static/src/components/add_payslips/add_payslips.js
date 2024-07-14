/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

import { Component, } from "@odoo/owl";

import { useAddPayslips } from '../../views/add_payslips_hook';

export class AddPayslips extends Component {
    setup() {
        super.setup();
        this.addPayslips = useAddPayslips();
    }

    async onAddPayslips() {
        await this.addPayslips(this.props.record);
    }
}
AddPayslips.template = "hr_payroll.AddPayslips";
AddPayslips.props = {
    ...standardWidgetProps,
    string: { type: String },
};

export const addPayslips = {
    component: AddPayslips,
    extractProps: ({ attrs }) => {
        const { string } = attrs;
        return { string };
    },
};
registry.category("view_widgets").add("add_payslips", addPayslips);
