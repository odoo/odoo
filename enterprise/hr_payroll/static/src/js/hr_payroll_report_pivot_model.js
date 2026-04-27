/** @odoo-module **/

import { PivotModel } from "@web/views/pivot/pivot_model";

export class HrPayrollReportPivotModel extends PivotModel {
    /**
     * @override
     */
    setup(params) {
        const countryCode = this.env.searchModel._context.country_code;
        if (countryCode) {
            for (var fieldName in params.metaData.fields) {
                if ((fieldName.startsWith('l10n') && !fieldName.startsWith('l10n_' + countryCode))
                    || (fieldName.startsWith('x_l10n') && !fieldName.startsWith('x_l10n_' + countryCode) && !fieldName.startsWith('x_l10n_xx'))) {
                    delete params.metaData.fields[fieldName];
                }
            }
        }
        super.setup(...arguments);
    }
}
