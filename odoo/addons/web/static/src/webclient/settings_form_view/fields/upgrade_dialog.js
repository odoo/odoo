/** @odoo-module */

import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

import { Component } from "@odoo/owl";

export class UpgradeDialog extends Component {
    setup() {
        this.orm = useService("orm");
        this.router = useService("router");
    }
    async _confirmUpgrade() {
        const usersCount = await this.orm.call("res.users", "search_count", [
            [["share", "=", false]],
        ]);
        window.open("https://www.odoo.com/odoo-enterprise/upgrade?num_users=" + usersCount, "_blank");
        this.props.close();
    }
}
UpgradeDialog.template = "web.UpgradeDialog";
UpgradeDialog.components = { Dialog };
