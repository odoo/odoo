import { Component, onWillDestroy, xml } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";

const MINUTE = 60 * 1000;
const HOUR = 60 * MINUTE;

export class RelativeTime extends Component {
    static props = ["datetime"];
    static template = xml`<t t-esc="relativeTime"/>`;

    setup() {
        super.setup();
        this.timeout = null;
        this.computeRelativeTime();
        onWillDestroy(() => clearTimeout(this.timeout));
    }

    computeDeltaAndRelativeTime() {
        const delta = Date.now() - this.props.datetime.ts;
        let relativeTime;
        if (delta < 45 * 1000) {
            relativeTime = _t("now");
        } else {
            relativeTime = this.props.datetime.toRelative();
        }
        return [delta, relativeTime];
    }

    computeRelativeTime() {
        if (!this.props.datetime) {
            this.relativeTime = "";
            return;
        }
        let delta;
        [delta, this.relativeTime] = this.computeDeltaAndRelativeTime();
        const updateDelay = delta < HOUR ? MINUTE : HOUR;
        if (updateDelay) {
            this.timeout = setTimeout(() => {
                this.computeRelativeTime();
                this.render();
            }, updateDelay);
        }
    }
}
