/* @odoo-module */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

/**
 * @typedef {Object} Props
 * @property {import("@mail/core/thread_model").Thread} thread
 * @property {import("@mail/web/suggested_recipient").SuggestedRecipient} recipient
 * @extends {Component<Props, Env>}
 */
export class SuggestedRecipient extends Component {
    static template = "mail.SuggestedRecipients";
    static props = ["thread", "recipient"];

    setup() {
        this.dialogService = useService("dialog");
        /** @type {import("@mail/core/thread_service").ThreadService)}*/
        this.threadService = useService("mail.thread");
    }

    get titleText() {
        return sprintf(
            _t("Add as recipient and follower (reason: %s)"),
            this.props.recipient.reason
        );
    }

    onChangeCheckbox(ev) {
        this.props.recipient.checked = !this.props.recipient.checked;
        if (this.props.recipient.checked && !this.props.recipient.persona) {
            this.props.recipient.checked = false;
            // Recipients must always be partners. On selecting a suggested
            // recipient that does not have a partner, the partner creation form
            // should be opened.
            this.dialogService.add(FormViewDialog, {
                context: {
                    active_id: this.props.thread.id,
                    active_model: "mail.compose.message",
                    default_email: this.props.recipient.email,
                    default_name: this.props.recipient.name,
                    default_lang: this.props.recipient.lang,
                    force_email: true,
                    ref: "compound_context",
                },
                onRecordSaved: () =>
                    this.threadService.fetchData(this.props.thread, ["suggestedRecipients"]),
                resModel: "res.partner",
                title: _t("Please complete customer's information"),
            });
        }
    }
}
