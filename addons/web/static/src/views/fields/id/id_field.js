import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class IdField extends Component {
    static template = "web.IdField";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.actionService = useService("action");
    }

    get value() {
        return this.props.record.data[this.props.name];
    }

    onIdClick() {
        this.actionService.doAction({
            res_id: this.value,
            res_model: this.props.record.resModel,
            type: "ir.actions.act_window",
            views: [[false, "form"]],
        });
    }
}

export const idField = {
    component: IdField,
    displayName: _t("Id"),
    supportedTypes: ["integer"],
    listViewWidth: () => [70, 136],
    isEmpty: (record, fieldName) => record.data[fieldName] === false,
};

registry.category("fields").add("id", idField);
