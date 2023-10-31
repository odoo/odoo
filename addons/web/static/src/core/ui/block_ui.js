/** @odoo-module **/

import { browser } from "@web/core/browser/browser";

const { Component, tags, useState } = owl;

export class BlockUI extends Component {
    setup() {
        this.messagesByDuration = [
            { time: 20, l1: this.env._t("Loading...") },
            { time: 40, l1: this.env._t("Still loading...") },
            {
                time: 60,
                l1: this.env._t("Still loading..."),
                l2: this.env._t("Please be patient."),
            },
            {
                time: 180,
                l1: this.env._t("Don't leave yet,"),
                l2: this.env._t("it's still loading..."),
            },
            {
                time: 120,
                l1: this.env._t("You may not believe it,"),
                l2: this.env._t("but the application is actually loading..."),
            },
            {
                time: 3180,
                l1: this.env._t("Take a minute to get a coffee,"),
                l2: this.env._t("because it's loading..."),
            },
            {
                time: null,
                l1: this.env._t(
                    "Maybe you should consider reloading the application by pressing F5..."
                ),
            },
        ];
        this.state = useState({
            blockUI: false,
            line1: "",
            line2: "",
        });

        this.props.bus.on("BLOCK", this, this.block);
        this.props.bus.on("UNBLOCK", this, this.unblock);
    }

    replaceMessage(index) {
        const message = this.messagesByDuration[index];
        this.state.line1 = message.l1;
        this.state.line2 = message.l2 || "";
        if (message.time !== null) {
            this.msgTimer = browser.setTimeout(() => {
                this.replaceMessage(index + 1);
            }, message.time * 1000);
        }
    }

    block() {
        this.state.blockUI = true;
        this.replaceMessage(0);
    }

    unblock() {
        this.state.blockUI = false;
        clearTimeout(this.msgTimer);
        this.state.line1 = "";
        this.state.line2 = "";
    }
}

BlockUI.template = tags.xml`
    <div t-att-class="state.blockUI ? 'o_blockUI' : ''">
      <t t-if="state.blockUI">
        <div class="o_spinner">
            <img src="/web/static/img/spin.png" alt="Loading..."/>
        </div>
        <div class="o_message">
            <t t-raw="state.line1"/> <br/>
            <t t-raw="state.line2"/>
        </div>
      </t>
    </div>`;
