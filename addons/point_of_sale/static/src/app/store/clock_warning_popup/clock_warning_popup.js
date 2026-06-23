import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useTime } from "@point_of_sale/app/utils/time_hook";

const { DateTime, Duration } = luxon;

export class ClockWarningPopup extends Component {
    static template = "point_of_sale.ClockWarningPopup";
    static components = { Dialog };
    static props = {
        close: Function,
        driftMinutes: Number,
        onContinue: Function,
        onCancel: Function,
    };

    setup() {
        this.time = useTime();
        this.timezone = DateTime.now().toFormat("ZZ");
    }

    get formattedDrift() {
        const d = Duration.fromObject({ minutes: this.props.driftMinutes }).shiftTo(
            "years",
            "days",
            "hours",
            "minutes"
        );
        const parts = [
            [Math.floor(d.years), _t("year"), _t("years")],
            [Math.floor(d.days), _t("day"), _t("days")],
            [Math.floor(d.hours), _t("hour"), _t("hours")],
            [Math.floor(d.minutes), _t("minute"), _t("minutes")],
        ];
        return (
            parts
                .filter(([n]) => n > 0)
                .map(([n, singular, plural]) => `${n} ${n === 1 ? singular : plural}`)
                .join(" ") || `0 ${_t("minutes")}`
        );
    }

    continueAnyway() {
        this.props.onContinue();
        this.props.close();
    }

    cancel() {
        this.props.onCancel();
        this.props.close();
    }
}
