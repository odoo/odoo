import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

export class ContractEndDialog extends Component {
    static template = "hr.ContractEndDialog";
    static components = { Dialog, Many2XAutocomplete };
    static props = {
        close: Function,
        record: Object,
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            reason: "correction",
            template: { id: false, name: "" },
        });
        this.onTemplateUpdate = this.onTemplateUpdate.bind(this);
    }

    get contractTemplateDomain() {
        return [["employee_id", "=", false]];
    }

    onTemplateUpdate(records) {
        if (records && records[0]) {
            this.state.template = { id: records[0].id, name: records[0].display_name };
        } else {
            this.state.template = { id: false, name: "" };
        }
    }

    onCorrectContract() {
        this.props.close({ reason: "correction" });
    }

    async onEndCollaboration() {
        const action = await this.orm.call(
            "hr.employee",
            "action_new_departure",
            [[this.props.record.resId]],
        );
        action.views = [[false, "form"]];
        action.context = {
            ...(action.context || {}),
            default_dismissal_date: this.props.record.data.contract_date_end,
        };

        this.props.close({ reason: "end_collaboration", action });
    }

    onDiscard() {
        this.props.close({ reason: "discard" });
    }

    async onNewContract() {
        this.props.close({
            reason: "new_contract",
            contractTemplateId: this.state.template.id || false,
        });
    }
}
