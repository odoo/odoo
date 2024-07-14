/** @odoo-module */
import { View } from "@web/views/view";
import { Component, useSubEnv } from "@odoo/owl";

export class BankRecViewEmbedder extends Component {
    static props = ["viewProps"];
    static template = "account_accountant.BankRecViewEmbedder";
    static components = { View };

    setup() {
        // Little hack while better solution from framework js.
        // Reset the config, especially the ControlPanel which was coming from a parent form view.
        // It also reset the view switchers which was necessary to make them disappear.
        useSubEnv({
            config: {...this.env.methods},
        });
    }
}
