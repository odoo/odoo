import { registry } from "@web/core/registry";
import {
    StateSelectionField,
    stateSelectionField,
} from "@web/views/fields/state_selection/state_selection_field";

const STATUS_COLORS = {
    blocked: "red",
    done: "green",
    waiting: "orange",
};

export class HrApplicantStateSelectionField extends StateSelectionField {
    setup() {
        super.setup();
        this.colors = STATUS_COLORS;
    }
}

export const hrApplicantStateSelectionField = {
    ...stateSelectionField,
    component: HrApplicantStateSelectionField,
};

registry.category("fields").add("hr_applicant_state_selection", hrApplicantStateSelectionField);
