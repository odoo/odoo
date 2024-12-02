import { Component } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class HrPresenceStatus extends Component {
    static template = "hr.HrPresenceStatus";
    static props = {
        ...standardFieldProps,
    };

    get label() {
        return this.value !== false
            ? this.options.find(([value, label]) => value === this.value)[1]
            : "";
    }

    get options() {
        return this.props.record.fields[this.props.name].selection.filter(
            (option) => option[0] !== false && option[1] !== ""
        );
    }

    get value() {
        return this.props.record.data[this.props.name];
    }

    get string(){
        if(this.value.includes("presence")) {
            return _t("Present");
        }
    }

    styleFunction(c1, c2, c3) {
        return `background-color: ${c1}; border-color:${c2}; color: ${c3};`
    }

    get style()  {
        if(this.value.includes("presence")) {
            return this.styleFunction("#10431c", 'green', 'green');
        }
    }
}

export const hrPresenceStatus = {
    component: HrPresenceStatus,
    displayName: _t("HR Presence Status"),
};

registry.category("fields").add("hr_presence_status", hrPresenceStatus)
