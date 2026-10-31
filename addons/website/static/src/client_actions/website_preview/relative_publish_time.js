import { incrementFn } from "@mail/utils/common/signal";

import { Component, computed, onWillDestroy, props, signal, types, xml } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";

const MINUTE = 60 * 1000;
const HOUR = 60 * MINUTE;

export class RelativePublishTime extends Component {
    static template = xml`<t t-out="this.relativeTime()"/>`;

    setup() {
        super.setup();
        this.recomputeSignal = signal(0);
        this.props = props({
            datetime: types.instanceOf(luxon.DateTime).optional(),
            negativeDeltaCallback: types.function().optional(),
        });
        this.timeout = null;
        onWillDestroy(() => clearTimeout(this.timeout));
        this.relativeTime = computed(() => {
            void this.recomputeSignal();
            clearTimeout(this.timeout);
            const datetime = this.props.datetime;
            if (!datetime) {
                return "";
            }
            const delta = datetime.ts - Date.now();
            if (delta < 0) {
                // The callback changes the state of the parent: not during a render.
                this.timeout = setTimeout(() => this.props.negativeDeltaCallback?.());
                return "";
            }
            this.timeout = setTimeout(
                incrementFn(this.recomputeSignal),
                delta < HOUR ? MINUTE : HOUR
            );
            if (delta < MINUTE) {
                return _t("Published shortly");
            }
            return _t("Published %(datetime)s", { datetime: datetime.toRelative() });
        });
    }
}
