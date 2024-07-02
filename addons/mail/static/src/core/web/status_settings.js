import { Component, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";

export class StatusSettings extends Component {
    static components = { Dropdown, DropdownItem };
    static props = ["close?"];
    static template = "discuss.StatusSettings";

    setup() {
        this.orm = useService("orm");
        this.store = useState(useService("mail.store"));
        this.actionService = useService("action");
    }

    onClickViewProfile() {
        const action = {
            res_id: this.store.self.id,
            res_model: "res.partner",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
        };
        this.actionService.doAction(action);
    }

    async setStatus(to) {
        rpc("/mail/im_status", { action: to });
        this.store.self.im_status = to;
    }

    async onClickSetCustomStatus() {
        const actionDescription = await this.orm.call("res.users", "action_custom_status");
        actionDescription.res_id = this.store.self.userId;
        actionDescription.context = { dialog_size: "medium" };
        const options = {
            onClose: async () => {
                const [user] = await this.orm.read(
                    "res.users",
                    [this.store.self.userId],
                    ["custom_im_status"]
                );
                this.store.self.custom_im_status = user.custom_im_status;
            },
        };
        await this.actionService.doAction(actionDescription, options);
    }
}
