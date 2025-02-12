import { statusBarField, StatusBarField } from "@web/views/fields/statusbar/statusbar_field";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class StatusBarEmployeeHistory extends StatusBarField {

    /** @override **/
    setup() {
        this.actionService = useService("action");
        return super.setup();
    }

    /** @override **/
    async selectItem(item) {
        debugger
        const { name, record } = this.props;
        const value = this.field.type === "many2one" ? [item.value, item.label] : item.value;
        await record.update({ [name]: value });
        await record.save();
        await this.actionService.doAction({
                type: 'ir.actions.act_window',
                res_model: 'hr.employee.history',
                res_id: item.value,
                views: [[false, "form"]],
            },
            {clearBreadcrumbs: true});
    }
}

export const statusBarEmployeeHistory = {
    ...statusBarField,
    component: StatusBarEmployeeHistory,
    additionalClasses: [ 'o_field_statusbar' ]
}
registry.category("fields").add("statusbar_employee_history", statusBarEmployeeHistory);
