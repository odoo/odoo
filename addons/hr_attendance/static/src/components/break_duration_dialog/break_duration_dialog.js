import { Component, props, proxy, t } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";

export class BreakDurationDialog extends Component {
    static template = "hr_attendance.BreakDurationDialog";
    static components = { Dialog };
    props = props({
        employeeName: t.string().optional(),
        onConfirm: t.function(),
        close: t.function(),
    });

    setup() {
        this.notification = useService("notification");
        this.state = proxy({ minutes: 0 });
        this.dialogTitle = _t("Break Duration");
        this.promptText = this.props.employeeName
            ? sprintf(
                  _t("Enter the total break duration (in minutes) for %s."),
                  this.props.employeeName
              )
            : _t("Enter the total break duration in minutes.");
    }

    async confirm() {
        const rawMinutes = this.state.minutes;
        const minutes = Number(rawMinutes);
        if (
            rawMinutes === "" ||
            !Number.isFinite(minutes) ||
            !Number.isInteger(minutes) ||
            minutes < 0
        ) {
            this.notification.add(_t("Enter a valid break duration in whole minutes."), {
                type: "danger",
            });
            return;
        }
        await this.props.onConfirm(minutes);
        this.props.close();
    }
}
