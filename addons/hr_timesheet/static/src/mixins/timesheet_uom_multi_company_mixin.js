/** @odoo-module */

import { useService } from "@web/core/utils/hooks";

const { onWillStart } = owl;

export const TimesheetUOMMultiCompanyMixin = (component) => class extends component {
    setup() {
        super.setup();
        this.companyService = useService('company');
        onWillStart(() => {
            this.currentCompanyTimesheetUOMFactor = this.companyService.currentCompany.timesheet_uom_factor || 1;
        });
    }
};
