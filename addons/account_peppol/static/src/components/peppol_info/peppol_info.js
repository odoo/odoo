/** @odoo-module **/
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import {_t} from "@web/core/l10n/translation";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";


class WhatIsPeppol extends Component {
    static props = { ...standardActionServiceProps };
    static template = "account_peppol.WhatIsPeppol";

    setup() {
        super.setup();
        this.actionService = useService("action");
    }

    closeButtonLabel() {
        if (this.props.action.context.action_on_activate.res_model === "peppol.registration") {
            return _t("Activate")
        } else {
            return _t("Got it !")
        }
    }

    activate() {
        const action = this.props.action.context.action_on_activate;
        this.actionService.doAction({
            name: action.name,
            type: action.type,
            res_model: action.res_model,
            views: [[false, action.view_mode]],
            target: action.target,
            context: action.context,
        });
    }
}

registry.category("actions").add("account_peppol.what_is_peppol", WhatIsPeppol);
