import { RelativeTime } from "@mail/core/common/relative_time";

import { _t } from "@web/core/l10n/translation";

const MINUTE = 60 * 1000;
const HOUR = 60 * MINUTE;

export class RelativePublishTime extends RelativeTime {
    static props = {
        ...RelativeTime.props,
        negativeDeltaCallback: {
            type: Function,
            optional: true,
        },
    };

    computeRelativeTime(datetime) {
        if (!datetime) {
            this.relativeTime = "";
            return;
        }
        const delta = datetime.ts - Date.now();
        if (delta < 0) {
            this.props.negativeDeltaCallback();
            clearTimeout(this.timeout);
        } else if (delta < MINUTE) {
            this.relativeTime = _t("Published shortly");
        } else {
            this.relativeTime = _t("Published %(datetime)s", {
                datetime: datetime.toRelative(),
            });
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
