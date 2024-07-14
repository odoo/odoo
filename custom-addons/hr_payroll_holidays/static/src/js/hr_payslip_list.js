/** @odoo-module **/

import { TimeOffToDeferWarning, useTimeOffToDefer } from "@hr_payroll_holidays/views/hooks";
import { registry } from "@web/core/registry";
import { ListRenderer } from "@web/views/list/list_renderer";
import { listView } from "@web/views/list/list_view";

class PayslipListRenderer extends ListRenderer {
    setup() {
        super.setup();
        this.timeOff = useTimeOffToDefer();
    }
}
PayslipListRenderer.template = "hr_payroll_holidays.PayslipListRenderer";
PayslipListRenderer.components = { ...ListRenderer.components, TimeOffToDeferWarning };
const PayslipListView = {
    ...listView,
    Renderer: PayslipListRenderer,
};

registry.category("views").add("hr_payroll_payslip_tree", PayslipListView);
