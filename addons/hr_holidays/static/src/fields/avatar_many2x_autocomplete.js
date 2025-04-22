import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { patch } from "@web/core/utils/patch";

import { getOutOfOfficeDateEndText } from "@hr_holidays/persona_model_patch";

patch(Many2XAutocomplete.prototype, {
    get searchSpecification() {
        if (
            !["res.users", "res.partner", "hr.employee", "resource.resource"].includes(
                this.props.resModel
            )
        ) {
            return super.searchSpecification;
        }
        return {
            ...super.searchSpecification,
            leave_date_to: {},
        };
    },
    mapRecordToOption(record) {
        if (
            !["res.users", "res.partner", "hr.employee", "resource.resource"].includes(
                this.props.resModel
            )
        ) {
            return super.mapRecordToOption(record);
        }
        const res = { ...super.mapRecordToOption(record) };
        if (record.leave_date_to) {
            res.outOfOffice = getOutOfOfficeDateEndText(record.leave_date_to);
        }
        return res;
    },
});
