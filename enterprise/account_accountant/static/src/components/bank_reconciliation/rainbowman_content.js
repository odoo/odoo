/** @odoo-module **/
import { BankRecFinishButtons } from "./finish_buttons";
import { Component, onMounted, onWillUnmount } from "@odoo/owl";

export class BankRecRainbowContent extends Component {
    static template = "account_accountant.BankRecRainbowContent";
    static components = { BankRecFinishButtons };
    static props = {};

    setup() {
        onWillUnmount(() => {
            this.env.methods.initReconCounter();
        });
        onMounted(() => {
            document.querySelector(".o_reward").style.pointerEvents = "none";
            document.querySelector(".o_reward_msg").style.pointerEvents = "auto";
        });
    }
}
