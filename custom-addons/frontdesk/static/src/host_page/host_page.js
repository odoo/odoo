/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useRef } from "@odoo/owl";
import { Many2One } from "./many2one/many2one";

export class HostPage extends Component {
    setup() {
        this.buttonRef = useRef("button");
    }

    /**
     * This method disables the confirm button.
     * When the text in the input field is not present in the selection.
     *
     * @param {Boolean} isDisable
     */
    disableButton(isDisable) {
        this.buttonRef.el.disabled = isDisable;
    }

    /**
     * This method is triggered when the confirm button is clicked.
     * It sets the host data and displays the RegisterPage component.
     *
     * @private
     */
    _onConfirm() {
        this.props.setHostData(this.host);
        this.props.showScreen("RegisterPage");
    }

    /**
     * @param {Object} host
     */
    selectedHost(host) {
        this.host = host;
    }
}

HostPage.template = "frontdesk.HostPage";
HostPage.components = { Many2One };
HostPage.props = {
    setHostData: Function,
    showScreen: Function,
    stationId: Number,
    token: String,
};

registry.category("frontdesk_screens").add("HostPage", HostPage);
