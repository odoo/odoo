import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class ProgressBar extends Component {
    static template = "point_of_sale.ProgressBar";
    static props = {
        currentValue: { type: Number, required: true },
        maxValue: { type: Number, required: true },
        addressNeeded: { type: Boolean, required: true },
    };

    remainingTime() {
        const minutes = this.props.currentValue;
        if (minutes >= 1440) {
            const days = Math.floor(minutes / 1440);
            return days === 1 ? _t("1 day left") : _t("%s days left", days);
        }
        if (minutes >= 60) {
            const hours = Math.floor(minutes / 60);
            return hours === 1 ? _t("1 hour left") : _t("%s hours left", hours);
        }
        return _t("%s min. left", minutes);
    }

    get barWidth() {
        return (
            (Math.max(0, this.props.maxValue - this.props.currentValue) / this.props.maxValue) * 100
        );
    }
}
