/** @odoo-module **/

import { ControlPanel } from "@web/search/control_panel/control_panel";
import { useService } from "@web/core/utils/hooks";
import { Component, markup } from "@odoo/owl";
import { SignRefusalDialog } from "@sign/dialogs/dialogs";

export class SignableRequestControlPanel extends Component {
    setup() {
        this.controlPanelDisplay = {};
        this.action = useService("action");
        this.orm = useService("orm");
        this.user = useService("user");
        this.dialog = useService("dialog");
        this.signInfo = useService("signInfo");
    }

    refuseDocument() {
        this.dialog.add(SignRefusalDialog);
    }

    get markupSignerStatus() {
        return markup(this.props.signerStatus.innerHTML);
    }

    toggleEditBar() {
        this.env.editWhileSigningBus.trigger("toggleEditBar");
    }
}

SignableRequestControlPanel.template = "sign.SignSignableRequestControlPanel";
SignableRequestControlPanel.components = {
    ControlPanel,
};
