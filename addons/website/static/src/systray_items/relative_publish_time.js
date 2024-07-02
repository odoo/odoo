import { RelativeTime } from "@mail/core/common/relative_time";
import { _t } from "@web/core/l10n/translation";

const MINUTE = 60 * 1000;

export class RelativePublishTime extends RelativeTime {
    static props = {
        datetime: Object,
        negativeDeltaCallback: {
            type: Function,
            optional: true,
        },
    };
    /**
     * @override
     */
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
