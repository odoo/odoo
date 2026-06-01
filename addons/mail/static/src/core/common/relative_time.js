import { Component, computed, onWillDestroy, props, signal, types, xml } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";

const MINUTE = 60 * 1000;
const HOUR = 60 * MINUTE;

export class RelativeTime extends Component {
    static template = xml`<t t-out="this.relativeTime()"/>`;

    recompute = signal(0);
    setup() {
        super.setup();
        this.props = props({
            datetime: types.instanceOf(luxon.DateTime),
        });
        this.timeout = null;
        onWillDestroy(() => clearTimeout(this.timeout));
        this.relativeTime = computed(() => {
            void this.recompute();
            clearTimeout(this.timeout);
            return this.computeRelativeTime();
        });
    }

    computeRelativeTime() {
        const delta = Date.now() - this.props.datetime.ts;
        const absDelta = Math.abs(delta);
        const updateDelay = absDelta < MINUTE ? absDelta : absDelta < HOUR ? MINUTE : HOUR;
        this.timeout = setTimeout(() => {
            this.recompute.set(this.recompute() + 1);
        }, updateDelay);
        if (absDelta < 45 * 1000) {
            return delta < 0 ? _t("in a few seconds") : _t("now");
        }
        return this.props.datetime.toRelative();
    }
}
