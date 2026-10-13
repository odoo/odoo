import { incrementFn } from "@mail/utils/common/signal";

import { Component, computed, onWillDestroy, signal, t, useProps, xml } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";

const MINUTE = 60 * 1000;
const HOUR = 60 * MINUTE;

export class RelativePublishTime extends Component {
    static template = xml`<t t-out="this.relativeTime()"/>`;

    props = useProps({
        datetime: t.instanceOf(luxon.DateTime).optional(),
        negativeDeltaCallback: t.function().optional(),
    });

    setup() {
        this.recomputeSignal = signal(0);
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
                // Not during a render: the callback changes the parent state.
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
