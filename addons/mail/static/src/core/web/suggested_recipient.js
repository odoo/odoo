import { Component } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

/**
 * @typedef {Object} Props
 * @property {function} onSuggestedRecipientAdded
 * @property {import("models").Thread} thread
 * @property {import("@mail/core/web/suggested_recipient").SuggestedRecipient} recipient
 * @extends {Component<Props, Env>}
 */
export class SuggestedRecipient extends Component {
    static template = "mail.SuggestedRecipients";
    static props = ["thread", "recipient", "onSuggestedRecipientAdded"];

    setup() {
        super.setup();
        this.dialogService = useService("dialog");
    }

    get name() {
        return this.props.recipient.name || this.props.recipient.display_name;
    }

    get titleText() {
        return _t("Add as recipient and follower (reason: %s)", this.props.recipient.reason);
    }

    onChangeCheckbox(ev) {
        this.props.recipient.checked = !this.props.recipient.checked;
        if (this.props.recipient.checked && !this.props.recipient.persona) {
            this.props.recipient.checked = false;
            // Recipients must always be partners. On selecting a suggested
            // recipient that does not have a partner, the partner creation form
            // should be opened.
            const thread = this.props.thread;
            this.dialogService.add(FormViewDialog, {
                context: {
                    active_id: thread.id,
                    active_model: "mail.compose.message",
                    default_email: this.props.recipient.email,
                    default_name: this.props.recipient.name,
                    default_lang: this.props.recipient.lang,
                    ...Object.fromEntries(
                        Object.entries(this.props.recipient.create_values).map(([k, v]) => [
                            "default_" + k,
                            v,
                        ])
                    ),
                    force_email: true,
                    ref: "compound_context",
                },
                onRecordSaved: () => this.props.onSuggestedRecipientAdded(thread),
                resModel: "res.partner",
                title: _t("Please complete customer's information"),
            });
        }
    }
}
