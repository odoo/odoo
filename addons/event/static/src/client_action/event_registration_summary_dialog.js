/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

export class EventRegistrationSummaryDialog extends Component {
    setup() {
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.orm = useService("orm");
    }

    get registration() {
        return this.props.registration;
    }

    get needManualConfirmation() {
        return this.registration.status === "need_manual_confirmation";
    }

    async onRegistrationConfirm() {
        await this.orm.call("event.registration", "action_set_done", [this.registration.id]);
        this.notification.add(_t("Registration confirmed"));
        this.props.close();
    }

    onRegistrationPrintPdf() {
        this.actionService.doAction({
            type: "ir.actions.report",
            report_type: "qweb-pdf",
            report_name: `event.event_registration_report_template_badge/${this.registration.id}`,
        });
    }

    async onRegistrationView() {
        await this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "event.registration",
            res_id: this.registration.id,
            views: [[false, "form"]],
            target: "current",
        });
        this.props.close();
    }
}
EventRegistrationSummaryDialog.template = "event.EventRegistrationSummaryDialog";
EventRegistrationSummaryDialog.components = { Dialog };
EventRegistrationSummaryDialog.props = {
    close: Function,
    registration: Object,
};
