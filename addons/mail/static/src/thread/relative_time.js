/** @odoo-module */

import { Component, xml, onWillDestroy } from "@odoo/owl";

const MINUTE = 60_000;
const HOUR = 60 * MINUTE;

export class RelativeTime extends Component {
    static template = xml`<t t-esc="relativeTime"/>`;
    static props = ["datetime"];

    setup() {
        this.computeRelativeTime();
        this.timeout = null;
        onWillDestroy(() => clearTimeout(this.timeout));
    }

    computeRelativeTime() {
        const datetime = this.props.datetime;
        if (!datetime) {
            this.relativeTime = "";
            return;
        }
        const delta = Date.now() - datetime.ts;
        if (delta < 45_000) {
            this.relativeTime = this.env._t("now");
        } else {
            this.relativeTime = datetime.toRelative();
        }
        const updateDelay = delta < HOUR ? MINUTE : HOUR;
        if (updateDelay) {
            this.timeout = setTimeout(() => {
                this.computeRelativeTime();
                this.render();
            }, updateDelay);
        }
    }
}
