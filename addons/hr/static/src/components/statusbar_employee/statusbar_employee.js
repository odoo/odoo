import { statusBarField, StatusBarField } from "@web/views/fields/statusbar/statusbar_field";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class StatusBarEmployee extends StatusBarField {

    /** @override **/
    setup() {
        this.actionService = useService("action");
        return super.setup();
    }

    /** @override **/
    async selectItem(item) {
        debugger
        const { name, record } = this.props;
        await record.save();  // We save first then change the selected version and save again
        const value = this.field.type === "many2one" ? [item.value, item.label] : item.value;
        await record.update({ [name]: value });
        await record.save();
    }
}

export const statusBarEmployee = {
    ...statusBarField,
    component: StatusBarEmployee,
    additionalClasses: [ 'o_field_statusbar' ]
}
registry.category("fields").add("statusbar_employee", statusBarEmployee);
