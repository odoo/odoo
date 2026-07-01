import { Component, proxy } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";

export class BreakDurationDialog extends Component {
    static template = "hr_attendance.BreakDurationDialog";
    static components = { Dialog };
    static props = {
        employeeName: { type: String, optional: true },
        defaultMinutes: { type: Number, optional: true },
        maxMinutes: { type: Number, optional: true },
        onConfirm: { type: Function },
        onCancel: { type: Function, optional: true },
        close: { type: Function },
    };

    setup() {
        this.notification = useService("notification");
        this.state = proxy({
            minutes: this.props.defaultMinutes ?? 0,
        });
        this.dialogTitle = _t("Break Duration");
        this.promptText = this.props.employeeName
            ? sprintf(
                  _t("Enter the extra break duration (in minutes) for %s."),
                  this.props.employeeName
              )
            : _t("Enter the extra break duration in minutes.");
    }

    get maxMinutes() {
        if (typeof this.props.maxMinutes !== "number") {
            return null;
        }
        return Math.max(Math.floor(this.props.maxMinutes), 0);
    }

    async confirm(ev) {
        ev.preventDefault();
        const rawMinutes = this.state.minutes;
        const minutes = Number(rawMinutes);
        const maxMinutes = this.maxMinutes;
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
        if (maxMinutes !== null && minutes > maxMinutes) {
            this.notification.add(
                sprintf(_t("Break duration cannot exceed %s minutes."), maxMinutes),
                { type: "danger" }
            );
            return;
        }
        const shouldClose = await this.props.onConfirm(minutes);
        if (shouldClose !== false) {
            this.props.close();
        }
    }

    cancel() {
        if (this.props.onCancel) {
            this.props.onCancel();
        }
        this.props.close();
    }
}
