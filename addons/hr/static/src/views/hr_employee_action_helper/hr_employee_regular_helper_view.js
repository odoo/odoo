import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class HrEmployeeRegularHelper extends Component {
    static template = "hr.EmployeeRegularHelper";
    static props = {
        showCreate: { type: Boolean },
    };

    setup() {
        super.setup();
        this._actionService = useService("action");
    }

    get showCreate() {
        return this.props.showCreate;
    }

    loadNewEmployeeForm() {
        this._actionService.doAction({
            name: _t("Employees"),
            res_model: "hr.employee",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
            view_mode: "form",
            target: "current",
        });
    }
}
