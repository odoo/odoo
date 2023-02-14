/* @odoo-module */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

/**
 * @typedef {Object} Props
 * @property {import("@mail/new/core/thread_model").Thread} thread
 * @property {import("@mail/new/web/suggested_recipient").SuggestedRecipient} recipient
 * @extends {Component<Props, Env>}
 */
export class SuggestedRecipient extends Component {
    static template = "mail.suggested_recipient";
    static props = ["thread", "recipient"];

    setup() {
        this.dialogService = useService("dialog");
        /** @type {import("@mail/new/core/thread_service").ThreadService)}*/
        this.threadService = useService("mail.thread");
    }

    get titleText() {
        return sprintf(
            _t("Add as recipient and follower (reason: %s)"),
            this.props.recipient.reason
        );
    }

    onChangeCheckbox() {
        if (this.props.recipient.persona) {
            this.props.recipient.checked = !this.props.recipient.checked;
        }
    }

    onClick() {
        if (!this.props.recipient.persona) {
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
                onRecordSaved: () => this._onDialogSaved(),
                resModel: "res.partner",
                title: _t("Please complete customer's information"),
            });
        }
    }

    async _onDialogSaved() {
        const data = await this.threadService.fetchData(
            this.props.thread.id,
            this.props.thread.model,
            ["suggestedRecipients"]
        );
        this.threadService.insertSuggestedRecipients(this.props.thread, data.suggestedRecipients);
    }
}
