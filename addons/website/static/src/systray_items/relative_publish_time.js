import { Component, onWillDestroy, xml } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";

const MINUTE = 60 * 1000;
const HOUR = 60 * MINUTE;

export class RelativePublishTime extends Component {
    static props = {
        datetime: Object,
        negativeDeltaCallback: {
            type: Function,
            optional: true,
        },
    };
    static template = xml`<t t-esc="relativeTime"/>`;

    setup() {
        super.setup();
        this.timeout = null;
        this.computeRelativeTime();
        onWillDestroy(() => clearTimeout(this.timeout));
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

    computeDeltaAndRelativeTime() {
        const delta = this.props.datetime.ts - Date.now();
        let relativeTime;
        if (delta < 0) {
            this.props.negativeDeltaCallback();
            clearTimeout(this.timeout);
        } else if (delta < MINUTE) {
            relativeTime = _t("Published shortly");
        } else {
            relativeTime = _t("Published %(datetime)s", {
                datetime: this.props.datetime.toRelative(),
            });
        }
        return [delta, relativeTime];
    }
}
