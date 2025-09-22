import { RelativeTime } from "@mail/core/common/relative_time";
import { _t } from "@web/core/l10n/translation";

const MINUTE = 60 * 1000;
const HOUR = 60 * MINUTE;

export class RelativePublishTime extends RelativeTime {
    static props = {
        datetime: {
            type: Object,
            optional: true,
        },
        negativeDeltaCallback: {
            type: Function,
            optional: true,
        },
    };

    computeRelativeTime(datetime) {
        if (this.timeout) {
            clearTimeout(this.timeout);
            this.timeout = null;
        }

        if (!datetime) {
            this.relativeTime = "";
            return;
        }

        const delta = datetime.ts - Date.now();

        if (delta < 0) {
            this.relativeTime = "";
            const callback = this.props.negativeDeltaCallback;
            if (typeof callback === "function") {
                callback();
            }
            return;
        }

        if (delta < MINUTE) {
            this.relativeTime = _t("Published shortly");
        } else {
            this.relativeTime = _t("Published %(datetime)s", {
                datetime: datetime.toRelative(),
            });
        }

        const updateDelay = delta < HOUR ? MINUTE : HOUR;

        this.timeout = setTimeout(() => {
            this.computeRelativeTime(this.props.datetime ?? datetime);
            this.render();
        }, updateDelay);
    }
}
