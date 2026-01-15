import { Component, onWillDestroy, onWillUpdateProps, xml } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";

const MINUTE = 60 * 1000;
const HOUR = 60 * MINUTE;

export class RelativeTime extends Component {
    static props = ["datetime"];
    static template = xml`<t t-esc="relativeTime"/>`;

    setup() {
        super.setup();
        this.timeout = null;
        this.computeRelativeTime(this.props.datetime);
        onWillDestroy(() => clearTimeout(this.timeout));
        onWillUpdateProps((nextProps) => {
            clearTimeout(this.timeout);
            this.computeRelativeTime(nextProps.datetime);
        });
    }

    computeRelativeTime(datetime) {
        if (!datetime) {
            this.relativeTime = "";
            return;
        }
        const delta = Date.now() - datetime.ts;
        const absDelta = Math.abs(delta);
        if (absDelta < 45 * 1000) {
            this.relativeTime = delta < 0 ? _t("in a few seconds") : _t("now");
        } else {
            this.relativeTime = datetime.toRelative();
        }
        const updateDelay = absDelta < MINUTE ? absDelta : absDelta < HOUR ? MINUTE : HOUR;
        this.timeout = setTimeout(() => {
            this.computeRelativeTime(this.props.datetime);
            this.render();
        }, updateDelay);
    }
}
