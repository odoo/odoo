import { Component, useRef, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";

export class BreakDurationDialog extends Component {
    static template = "hr_attendance.BreakDurationDialog";
    static components = { Dialog };
    static props = {
        employeeName: { type: String, optional: true },
        defaultMinutes: { type: Number, optional: true },
        onConfirm: { type: Function },
        onCancel: { type: Function, optional: true },
        close: { type: Function },
    };

    setup() {
        this.state = useState({
            minutes: this.props.defaultMinutes ?? 0,
        });
        this.durationInputRef = useRef("durationInput");
    }

    get title() {
        return _t("Break Duration");
    }

    get promptText() {
        if (this.props.employeeName) {
            return sprintf(_t("Enter the extra break duration (in minutes) for %s, excluding scheduled lunch."), this.props.employeeName);
        }
        return _t("Enter the extra break duration in minutes, excluding scheduled lunch.");
    }

    get minutesLabel() {
        return _t("minutes");
    }

    get confirmLabel() {
        return _t("Confirm");
    }

    get cancelLabel() {
        return _t("Cancel");
    }

    async confirm(ev) {
        ev.preventDefault();
        const input = this.durationInputRef.el;
        if (input && !input.reportValidity()) {
            return;
        }
        const shouldClose = await this.props.onConfirm(Number(this.state.minutes) || 0);
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
