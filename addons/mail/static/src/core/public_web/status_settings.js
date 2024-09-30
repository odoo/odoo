import { Component, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";
import { CustomStatusEditor } from "./custom_status_editor";

export class StatusSettings extends Component {
    static components = { Dropdown, DropdownItem, CustomStatusEditor };
    static props = ["close"];
    static template = "discuss.StatusSettings";

    setup() {
        this.store = useState(useService("mail.store"));
        this.actionService = useService("action");
    }

    onClickViewProfile() {
        const action = {
            res_id: this.store.self.id,
            res_model: "res.partner",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
            target: "new",
        };
        this.actionService.doAction(action);
    }
}
