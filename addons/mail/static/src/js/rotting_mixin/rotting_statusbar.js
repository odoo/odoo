import {
    statusBarDurationField,
    StatusBarDurationField,
} from "@mail/views/fields/statusbar_duration/statusbar_duration_field";
import { registry } from "@web/core/registry";
import { getRottingDaysCount, getRottingDaysTitle } from "./rotting_widget";

export class RottingStatusBarDurationField extends StatusBarDurationField {
    static template = "mail.RottingStatusBarDurationField";

    setup() {
        super.setup();
        this.title = getRottingDaysTitle(
            this.env.model.config.resModel,
            this.props.record.data.rotting_days
        );
    }

    get dayCount() {
        return getRottingDaysCount(this.props.record.data.rotting_days);
    }
}

export const rottingStatusBarDurationField = {
    ...statusBarDurationField,
    component: RottingStatusBarDurationField,
};

registry.category("fields").add("rotting_statusbar_duration", rottingStatusBarDurationField);
