import { Component, useState } from "@odoo/owl";
import { formatDuration } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class CallNotificationMessage extends Component {
    static template = "mail.CallNotificationMessage";
    static props = ["author", "messageDate", "dateStart", "dateEnd?"];

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
    }

    get callInformation() {
        if (this.props.dateStart.equals(this.props.dateEnd)) {
            return _t("started a call.");
        }
        return _t("started a call that lasted %(duration)s.", {
            duration: this.callDuration,
        });
    }

    get callDuration() {
        const diff = this.props.dateEnd.diff(this.props.dateStart, ["hours", "minutes", "seconds"]);
        // const diff = Duration.fromObject({ hours: 1, minutes: 0, seconds: 15 })
        const { hours, minutes } = diff.toObject();
        if (!hours && !minutes) {
            return _t("a few seconds");
        } else if (!hours && minutes === 1) {
            return _t("a minute");
        } else if (hours === 1 && !minutes) {
            return _t("an hour");
        }
        return formatDuration(diff.as("seconds"), true);
    }
}
