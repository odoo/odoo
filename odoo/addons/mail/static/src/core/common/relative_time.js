/* @odoo-module */

import { Component, onWillDestroy, xml } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";

const MINUTE = 60 * 1000;
const HOUR = 60 * MINUTE;

export class RelativeTime extends Component {
    static props = ["datetime"];
    static template = xml`<t t-esc="relativeTime"/>`;

    setup() {
        this.timeout = null;
        this.computeRelativeTime();
        onWillDestroy(() => clearTimeout(this.timeout));
    }

    computeRelativeTime() {
        const datetime = this.props.datetime;
        if (!datetime) {
            this.relativeTime = "";
            return;
        }
        const delta = Date.now() - datetime.ts;
        if (delta < 45 * 1000) {
            this.relativeTime = _t("now");
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
