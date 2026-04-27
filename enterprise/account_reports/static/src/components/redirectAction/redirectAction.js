/** @odoo-module */
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { Dialog } from "@web/core/dialog/dialog";

class RedirectAction extends Component {
    static template = "account_reports.redirectAction";
    static components = { Dialog };

    static props = {
        ...standardActionServiceProps,
        action: Object
    }

    setup() {
        this.actionService = useService("action");
    }

    openClientAction() {
        this.actionService.doAction(this.props.action.params.depending_action);
    }

    close() {
        this.actionService.doAction({type: 'ir.actions.act_window_close'});
    }
}

registry.category("actions").add("account_reports.redirect_action", RedirectAction);
