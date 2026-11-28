import { Component, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class PayInPosField extends Component {
    static template = "pos_sale.PayInPosField";
    static components = { Dropdown, DropdownItem };
    props = useProps(standardFieldProps);

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
    }

    async openPos(session) {
        // PoS loads the SO from the database, so pending edits must be saved first
        if (!(await this.props.record.save())) {
            return;
        }
        const action = await this.orm.call("sale.order", "action_pay_in_pos", [
            [this.props.record.resId],
            session.id,
        ]);
        await this.action.doAction(action);
    }
}

registry.category("fields").add("pay_in_pos", {
    component: PayInPosField,
    supportedTypes: ["json"],
});
