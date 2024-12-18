/** @odoo-module **/
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";


class WhatIsPeppol extends Component {
    static props = { ...standardActionServiceProps };
    static template = "account_peppol.WhatIsPeppol";

    setup() {
        super.setup();
        this.actionService = useService("action");
    }

    activate() {
        this.actionService.doAction({
            name: _t("Print & Send"),
            type: "ir.actions.act_window",
            res_model: "account.move.send.wizard",
            views: [[false, "form"]],
            target: "new",
            context: {
                active_model: "account.move",
                active_ids: Object.values(this.props.action.context.move_ids),
            },
        });
    }
}

registry.category("actions").add("account_peppol.what_is_peppol", WhatIsPeppol);
