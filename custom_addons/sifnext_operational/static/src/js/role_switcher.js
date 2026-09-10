/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";

export class SifnextRoleSwitcher extends Component {
    static template = "sifnext_operational.RoleSwitcher";

    static components = {
        Dropdown,
        DropdownItem,
    };

    setup() {
        this.rpc = useService("rpc");
    }

    async switchRole(role) {
        const result = await this.rpc(
            "/sifnext_operational/switch_role",
            {
                role: role,
            }
        );

        if (!result.success) {
            window.alert(result.message);
            return;
        }

        window.location.reload();
    }
}

registry.category("systray").add(
    "sifnext_operational.role_switcher",
    {
        Component: SifnextRoleSwitcher,
    },
    {
        sequence: 10,
    },
);